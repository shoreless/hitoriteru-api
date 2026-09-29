# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Validate content/*.yaml and write the published JSON under docs/v1/.

Run: uv run tools/build.py
Output:
  docs/v1/content.json   words + categories (schema below, mirrored by the app's ContentModels.kt)
  docs/v1/manifest.json  schema version, content version, sha256 of content.json
"""

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from romaji import to_romaji  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
OUT = ROOT / "docs" / "v1"
SCHEMA_VERSION = 1
CATEGORY_TYPES = {"meaning", "script", "shared_kanji", "counter", "reading"}

THEMED = 0  # min_level of categories used only by themes; the journey never deals them


def band_window(band: int) -> set[int]:
    """JLPT levels a journey band draws from (spec: Content level): N5 → {5}, N4 → {4,5}, N3 → {3,4,5}, N2 → {2,3,4}."""
    return set(range(band, min(5, band + 2) + 1))

_KANA = re.compile(r"[぀-ヿー]")
_BRACKET = re.compile(r"\[([^\]]+)\]")


def parse_furigana(text: str) -> list[dict]:
    """'自[じ]転[てん]車[しゃ]' → [{t:自,r:じ},{t:転,r:てん},{t:車,r:しゃ}].

    A bracket reads the run of non-kana characters right before it; kana stays plain.
    """
    segments: list[dict] = []
    pos = 0
    for m in _BRACKET.finditer(text):
        before = text[pos:m.start()]
        split = len(before)
        while split > 0 and not _KANA.match(before[split - 1]):
            split -= 1
        if split == len(before):
            raise ValueError(f"bracket without a kanji base in {text!r}")
        if before[:split]:
            segments.append({"t": before[:split]})
        segments.append({"t": before[split:], "r": m.group(1)})
        pos = m.end()
    if text[pos:]:
        segments.append({"t": text[pos:]})
    return segments


def plain(segments: list[dict]) -> str:
    return "".join(s["t"] for s in segments)


def reading_of(segments: list[dict]) -> str:
    return "".join(s.get("r", s["t"]) for s in segments)


def build_levels(raw: list[dict], errors: list[str]) -> list[dict]:
    levels = []
    previous = 0
    for i, r in enumerate(raw):
        where = f"levels.yaml entry {i + 1}"
        start = r.get("from")
        if not isinstance(start, int) or start <= previous:
            errors.append(f"{where}: from must increase (1 first)")
        if i == 0 and start != 1:
            errors.append(f"{where}: the first entry must start at level 1")
        previous = start if isinstance(start, int) else previous
        errors.extend(f"{where}: {e}" for e in board_shape_errors(r))
        low, high = (r.get("words_per_category") or [0, 0])
        if not 3 <= low <= high:
            errors.append(f"{where}: words_per_category must be [min, max] with 3 ≤ min ≤ max")
        if r.get("band") not in (1, 2, 3, 4, 5):
            errors.append(f"{where}: band must be 1–5")
        if not r.get("categories", 0) > r.get("foundations", 0) >= 2:
            errors.append(f"{where}: needs 2+ foundations and more categories than foundations")
        levels.append({
            "from": start, "band": r.get("band"), "categories": r.get("categories"),
            "foundations": r.get("foundations"), "columns": r.get("columns"),
            "wordsMin": low, "wordsMax": high, "slack": r.get("slack"),
        })
    return levels


def build_themes(raw: list[dict], categories: dict, errors: list[str]) -> list[dict]:
    themes = []
    seen = set()
    for t in raw:
        tid = t.get("id")
        where = f"theme {tid}"
        if not tid or tid in seen:
            errors.append(f"{where}: needs a unique id")
        seen.add(tid)
        chosen = t.get("categories") or []
        for cid in chosen:
            if cid not in categories:
                errors.append(f"{where}: unknown category {cid}")
        if not 3 <= len(chosen) <= 5:
            errors.append(f"{where}: needs 3–5 categories")
        if not len(chosen) > t.get("foundations", 0) >= 2:
            errors.append(f"{where}: needs 2+ foundations and more categories than foundations")
        errors.extend(f"{where}: {e}" for e in board_shape_errors(t))
        known = [categories[c] for c in chosen if c in categories]
        for c in known:
            for other in known:
                if other["id"] in c["excludes"]:
                    errors.append(f"{where}: {c['id']} excludes {other['id']}")
            usable = [m for m in c["members"] if not any(m in o["members"] for o in known if o is not c)]
            if len(usable) < 3:
                errors.append(f"{where}: {c['id']} keeps only {len(usable)} words once shared words are removed")
        title = parse_furigana(t.get("title", ""))
        themes.append({
            "id": tid, "title": plain(title), "titleFurigana": title,
            "titleEn": t.get("title_en", ""), "blurbEn": t.get("blurb_en", ""),
            "categories": chosen, "foundations": t.get("foundations"), "columns": t.get("columns"),
            "slack": t.get("slack"), "daily": bool(t.get("daily", False)),
        })
    return themes


def board_shape_errors(r: dict) -> list[str]:
    errors = []
    columns = r.get("columns")
    if not isinstance(columns, list) or not 3 <= len(columns) <= 5 or not all(isinstance(c, int) and c >= 1 for c in columns):
        errors.append("columns must list 3–5 column depths, each 1 or more")
    slack = r.get("slack")
    if not isinstance(slack, (int, float)) or not 1.2 <= slack <= 3.0:
        errors.append("slack must be between 1.2 and 3.0")
    return errors


def playability_warnings(words: list[dict], categories: list[dict], levels: list[dict]) -> list[str]:
    """Journey categories that can never be dealt at a band levels.yaml uses."""
    level_of = {w["id"]: w["jlpt"] for w in words}
    bands = {}
    for lv in levels:
        bands[lv["band"]] = max(bands.get(lv["band"], 0), lv["wordsMin"])
    warnings = []
    for c in categories:
        if c["minLevel"] == THEMED:
            continue
        playable = False
        for band, needed in sorted(bands.items(), reverse=True):
            if c["minLevel"] < band:
                continue  # category not allowed this easy
            usable = [m for m in c["members"] if level_of[m] in band_window(band)]
            if len(usable) >= needed:
                playable = True
            else:
                warnings.append(f"{c['id']} can't be dealt at N{band}: {len(usable)} members in range, needs {needed}")
        if not playable:
            warnings.append(f"{c['id']} never appears on a journey board yet")
    return warnings


class DuplicateKey(Exception):
    pass


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate keys, which plain YAML silently resolves by keeping the last one."""

    def construct_mapping(self, node, deep=False):
        seen = {}
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise DuplicateKey(f"{key!r} appears twice (lines {seen[key] + 1} and {key_node.start_mark.line + 1})")
            seen[key] = key_node.start_mark.line
        return super().construct_mapping(node, deep=deep)


def load_yaml(name: str):
    path = CONTENT / name
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        try:
            return yaml.load(f, Loader=StrictLoader)
        except DuplicateKey as e:
            raise SystemExit(f"content error: {name}: {e}")


def build() -> int:
    errors: list[str] = []
    raw_words = load_yaml("words.yaml") or {}
    raw_categories = load_yaml("categories.yaml") or []
    overrides = load_yaml("romaji_overrides.yaml") or {}

    words = []
    word_ids = set()
    for headword, w in raw_words.items():
        headword = str(headword)
        if "furigana" in w:
            segs = parse_furigana(w["furigana"])
            if plain(segs) != headword:
                errors.append(f"{headword}: furigana spells {plain(segs)!r}")
        else:
            segs = [{"t": headword}]
        reading = w.get("reading") or reading_of(segs)
        if _KANA.sub("", reading):
            errors.append(f"{headword}: reading {reading!r} is not all kana")
        glosses = w.get("glosses") or []
        if not 1 <= len(glosses) <= 3:
            errors.append(f"{headword}: needs 1–3 glosses")
        jlpt = w.get("jlpt")
        if jlpt not in (0, 1, 2, 3, 4, 5):
            errors.append(f"{headword}: jlpt must be 1–5, or 0 when not tagged")
        romaji = overrides.get(headword) or to_romaji(reading)
        words.append({
            "id": headword,
            "headword": headword,
            "reading": reading,
            "romaji": romaji,
            "furigana": segs,
            "pos": w.get("pos", "noun"),
            "glosses": [str(g) for g in glosses],
            "jlpt": jlpt,
        })
        word_ids.add(headword)

    categories = []
    cat_ids = {c["id"] for c in raw_categories}
    seen_ids = set()
    for c in raw_categories:
        if c["id"] in seen_ids:
            errors.append(f"category id {c['id']} is used twice")
        seen_ids.add(c["id"])
    for c in raw_categories:
        cid = c["id"]
        if c.get("type") not in CATEGORY_TYPES:
            errors.append(f"category {cid}: unknown type {c.get('type')!r}")
        members = [str(m) for m in c.get("members", [])]
        repeated = sorted({m for m in members if members.count(m) > 1})
        if repeated:
            errors.append(f"category {cid}: {', '.join(repeated)} listed twice")
        for m in members:
            if m not in word_ids:
                errors.append(f"category {cid}: member {m} is not in words.yaml")
        for ex in c.get("excludes", []):
            if ex not in cat_ids:
                errors.append(f"category {cid}: excludes unknown category {ex}")
        near_miss = {str(k): v for k, v in (c.get("near_miss") or {}).items()}
        for k in near_miss:
            if k not in members:
                errors.append(f"category {cid}: near_miss word {k} is not a member")
        if len(members) < 4:
            errors.append(f"category {cid}: needs at least 4 members")
        min_level = c.get("min_level")
        if min_level == "themed":
            min_level = THEMED
        elif min_level not in (1, 2, 3, 4, 5):
            errors.append(f"category {cid}: min_level must be 1–5 or themed")
        label_segs = parse_furigana(c["label"])
        categories.append({
            "id": cid,
            "type": c["type"],
            "label": plain(label_segs),
            "labelFurigana": label_segs,
            "labelEn": c["label_en"],
            "ruleEn": c["rule_en"],
            "minLevel": min_level,
            "members": members,
            "excludes": c.get("excludes", []),
            "nearMiss": near_miss,
        })

    levels = build_levels(load_yaml("levels.yaml") or [], errors)
    themes = build_themes(load_yaml("themes.yaml") or [], {c["id"]: c for c in categories}, errors)

    if errors:
        print("content errors:", *errors, sep="\n  ")
        return 1

    for warning in playability_warnings(words, categories, levels):
        print("warning:", warning)

    content = {"schemaVersion": SCHEMA_VERSION, "words": words, "categories": categories, "levels": levels, "themes": themes}
    body = json.dumps(content, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    digest = hashlib.sha256(body).hexdigest()

    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "manifest.json"
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    version = previous.get("contentVersion", 0)
    if previous.get("sha256") != digest:
        version += 1
    manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "contentVersion": version,
        "content": "content.json",
        "sha256": digest,
        "bytes": len(body),
        "words": len(words),
        "categories": len(categories),
        "levels": len(levels),
        "themes": len(themes),
        "builtAt": previous.get("builtAt") if previous.get("sha256") == digest
        else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (OUT / "content.json").write_bytes(body)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"content v{version}: {len(words)} words, {len(categories)} categories, {len(levels)} level ranges, "
          f"{len(themes)} themes, {len(body):,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(build())
