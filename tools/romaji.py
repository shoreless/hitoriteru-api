"""Kana to modified-Hepburn romaji with macrons (ō, ū, ā, ē, ī for katakana ー).

Kana alone can't separate a long vowel from a morpheme boundary (思う is omou, not omō),
so callers apply content/romaji_overrides.yaml on top of this.
"""

_BASE = {
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o",
    "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "さ": "sa", "し": "shi", "す": "su", "せ": "se", "そ": "so",
    "た": "ta", "ち": "chi", "つ": "tsu", "て": "te", "と": "to",
    "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no",
    "は": "ha", "ひ": "hi", "ふ": "fu", "へ": "he", "ほ": "ho",
    "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo",
    "や": "ya", "ゆ": "yu", "よ": "yo",
    "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro",
    "わ": "wa", "ゐ": "i", "ゑ": "e", "を": "o", "ん": "n",
    "が": "ga", "ぎ": "gi", "ぐ": "gu", "げ": "ge", "ご": "go",
    "ざ": "za", "じ": "ji", "ず": "zu", "ぜ": "ze", "ぞ": "zo",
    "だ": "da", "ぢ": "ji", "づ": "zu", "で": "de", "ど": "do",
    "ば": "ba", "び": "bi", "ぶ": "bu", "べ": "be", "ぼ": "bo",
    "ぱ": "pa", "ぴ": "pi", "ぷ": "pu", "ぺ": "pe", "ぽ": "po",
    "ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o", "ゔ": "vu",
}

_YOON = {"ゃ": "a", "ゅ": "u", "ょ": "o"}
# Katakana-only digraphs for loanwords (ティ, ファ, ウィ …): second char is a small vowel.
_SMALL_VOWEL = {"ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o"}
_MACRON = {"a": "ā", "i": "ī", "u": "ū", "e": "ē", "o": "ō"}


def _to_hiragana(text: str) -> str:
    out = []
    for ch in text:
        code = ord(ch)
        if 0x30A1 <= code <= 0x30F6:
            out.append(chr(code - 0x60))
        else:
            out.append(ch)
    return "".join(out)


def _syllables(kana: str):
    """Split hiragana into (romaji, is_katakana_long_mark) units."""
    units = []
    i = 0
    while i < len(kana):
        ch = kana[i]
        nxt = kana[i + 1] if i + 1 < len(kana) else ""
        if ch == "ー":
            units.append("ー")
            i += 1
            continue
        if ch == "っ":
            units.append("っ")
            i += 1
            continue
        base = _BASE.get(ch)
        if base is None:
            raise ValueError(f"unsupported kana {ch!r} in {kana!r}")
        if nxt in _YOON and base.endswith("i") and ch not in "あいうえお":
            stem = base[:-1]
            if stem in ("sh", "ch", "j"):
                units.append(stem + _YOON[nxt])
            else:
                units.append(stem + "y" + _YOON[nxt])
            i += 2
            continue
        if nxt in _SMALL_VOWEL and ch not in "あいうえおぁぃぅぇぉ":
            consonant = {"ふ": "f", "て": "t", "で": "d", "う": "w", "ゔ": "v", "し": "sh", "ち": "ch", "じ": "j"}.get(ch)
            if consonant:
                units.append(consonant + _SMALL_VOWEL[nxt])
                i += 2
                continue
        units.append(base)
        i += 1
    return units


def to_romaji(kana: str) -> str:
    hira = _to_hiragana(kana)
    units = _syllables(hira)
    out: list[str] = []
    for idx, unit in enumerate(units):
        if unit == "ー":
            if out and out[-1] and out[-1][-1] in _MACRON:
                out[-1] = out[-1][:-1] + _MACRON[out[-1][-1]]
            continue
        if unit == "っ":
            nxt = units[idx + 1] if idx + 1 < len(units) else ""
            if nxt.startswith("ch"):
                out.append("t")
            elif nxt and nxt[0] not in "aiueon":
                out.append(nxt[0])
            continue
        if unit == "n":
            nxt = units[idx + 1] if idx + 1 < len(units) else ""
            out.append("n'" if nxt and nxt[0] in "aiueoy" else "n")
            continue
        # Long vowels: おう / おお → ō, うう → ū, ああ → ā. い/え sequences stay (ii, ei).
        if unit in ("u", "o") and out:
            prev = out[-1]
            if prev and prev[-1] == "o" and unit in ("u", "o"):
                out[-1] = prev[:-1] + "ō"
                continue
            if prev and prev[-1] == "u" and unit == "u":
                out[-1] = prev[:-1] + "ū"
                continue
        if unit == "a" and out and out[-1] and out[-1][-1] == "a":
            out[-1] = out[-1][:-1] + "ā"
            continue
        out.append(unit)
    return "".join(out)


if __name__ == "__main__":
    cases = {
        "ぎゅうにゅう": "gyūnyū", "ひこうき": "hikōki", "おとうと": "otōto", "コーヒー": "kōhī",
        "じてんしゃ": "jitensha", "きっぷ": "kippu", "まっちゃ": "matcha", "ほんや": "hon'ya",
        "でんわ": "denwa", "おかあさん": "okāsan", "せんせい": "sensei", "ちいさい": "chiisai",
        "ジュース": "jūsu", "タクシー": "takushī", "パーティー": "pātī", "ファン": "fan",
        "でんしレンジ": "denshirenji", "ていでん": "teiden",
    }
    bad = {k: (to_romaji(k), v) for k, v in cases.items() if to_romaji(k) != v}
    print("ok" if not bad else bad)
