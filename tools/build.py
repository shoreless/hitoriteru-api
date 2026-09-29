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


def load_yaml(name: str):
    path = CONTENT / name
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


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
        if jlpt not in (1, 2, 3, 4, 5):
            errors.append(f"{headword}: jlpt must be 1–5")
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
    for c in raw_categories:
        cid = c["id"]
        if c.get("type") not in CATEGORY_TYPES:
            errors.append(f"category {cid}: unknown type {c.get('type')!r}")
        members = [str(m) for m in c.get("members", [])]
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
        label_segs = parse_furigana(c["label"])
        categories.append({
            "id": cid,
            "type": c["type"],
            "label": plain(label_segs),
            "labelFurigana": label_segs,
            "labelEn": c["label_en"],
            "ruleEn": c["rule_en"],
            "minLevel": c["min_level"],
            "members": members,
            "excludes": c.get("excludes", []),
            "nearMiss": near_miss,
        })

    if errors:
        print("content errors:", *errors, sep="\n  ")
        return 1

    content = {"schemaVersion": SCHEMA_VERSION, "words": words, "categories": categories}
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
        "builtAt": previous.get("builtAt") if previous.get("sha256") == digest
        else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (OUT / "content.json").write_bytes(body)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"content v{version}: {len(words)} words, {len(categories)} categories, {len(body):,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(build())
