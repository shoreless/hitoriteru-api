# hitoriteru-api

Content for the Hitoriteru Android app, served as static JSON from GitHub Pages.

**Writing content? Start with [CONTENT_GUIDE.md](CONTENT_GUIDE.md).**

## Layout

| Path | What |
| --- | --- |
| `content/words.yaml` | Hand-authored vocabulary (headword, furigana, glosses, JLPT level) |
| `content/categories.yaml` | Hand-curated categories, exclusions and near-miss notes |
| `content/romaji_overrides.yaml` | Optional per-word romaji fixes (`思う: omou`) |
| `tools/build.py` | Validates content and writes `docs/v1/` |
| `docs/v1/manifest.json` | Schema version, content version, sha256 of `content.json` |
| `docs/v1/content.json` | Words + categories consumed by the app |

## Build

```sh
uv run tools/build.py
```

The content version bumps automatically whenever `content.json` changes. Commit `docs/` with the source change.

## Serving

GitHub Pages serves `docs/` from `main`. The app reads
`https://<user>.github.io/hitoriteru-api/v1/manifest.json`, downloads `content.json` when its sha256
differs from the cached copy, and falls back to the snapshot bundled in the APK when offline.

`v1` is the schema version: a breaking change to the JSON shape goes to `v2/`, and `v1/` keeps serving
older app installs.

## Licences

Word data will come from JMdict / KANJIDIC2 (EDRDG, CC BY-SA 4.0). The derived `content.json` is covered
by ShareAlike; attribution appears in the app's About screen.
