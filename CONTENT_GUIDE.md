# Hitoriteru content guide

How to write words and categories for Hitoriteru. No coding needed: you edit two YAML files, run one command,
and push. The app picks up the new content within about a minute.

## The game in two minutes

Hitoriteru is a solitaire game for English speakers learning Japanese. It has three ways to play:

- **Journey:** numbered levels (Level 1, 2, 3…) that climb through the JLPT bands. Boards draw categories at random
  from those allowed at the band.
- **Themes:** curated levels around a situation, like *Going to the doctor*. Every word in the theme's categories
  is dealt, whatever its JLPT level.
- **Daily challenge:** one theme per day, the same theme for everyone. Solving it earns that day's crown.

Every board, in every mode, is shuffled fresh on the phone each time it's played, and checked to be winnable
before it's shown.

 Each board deals a shuffled deck of
**word cards** (雨, 電車, コーヒー) and **category cards** (天気 · weather). The player:

1. Places a category card on an empty **foundation** slot.
2. Finds that category's words among the face-down columns and the draw pile, and stacks them onto it.
3. Clears the board when every category is complete, within a fixed number of moves.

Words of the same category can also be stacked together in the columns first, and a category card can "cap"
such a run and carry it to a foundation in one move.

Learning happens at three moments, and they shape how you write content:

| Moment | What the player sees | Uses |
| --- | --- | --- |
| On the card | Headword, plus furigana and romaji depending on their reading-aid setting | `furigana`, `romaji` |
| Long-press a card | Reading, romaji, part of speech, glosses, JLPT level. **Never the word's category.** | `glosses`, `pos`, `jlpt` |
| Card lands on its foundation | A toast: `雨 · ame · rain` | first gloss |
| Card dropped on the wrong foundation | A short note, costing the player a move | `near_miss` |

The puzzle is working out which words belong together. **Anything that gives the category away before the
card is placed spoils the board**, so glosses must describe the word, not its group.

## Where content lives

```
content/
  words.yaml          every word the app can use
  categories.yaml     the groups words are sorted into
  themes.yaml         themed levels ("Going to the doctor"), also used by the daily challenge
  levels.yaml         the journey's difficulty curve
  romaji_overrides.yaml  (optional) fixes for romaji the build gets wrong
tools/build.py        checks everything and writes the JSON the app downloads
docs/v1/              the published JSON (generated — never edit by hand)
```

## Writing words (`content/words.yaml`)

One line per word, keyed by the headword:

```yaml
晴れ: { furigana: "晴[は]れ", pos: noun, glosses: [clear weather, sunny], jlpt: 5 }
コーヒー: { reading: コーヒー, pos: noun, glosses: [coffee], jlpt: 5 }
```

| Field | Rules |
| --- | --- |
| key | The headword exactly as it should appear on the card. It is also the word's id, so don't rename published words casually. |
| `furigana` | The headword with each kanji run's reading in brackets: `自[じ]転[てん]車[しゃ]`. Kana stays outside brackets: `お茶[ちゃ]`. Words read as a whole (jukujikun) take one bracket: `今日[きょう]`. **Always wrap it in quotes.** Omit for kana-only words. |
| `reading` | Only for kana-only words (the build derives it from `furigana` otherwise). |
| `pos` | Part of speech, lower case: `noun`, `verb`, `i-adjective`, `na-adjective`, `adverb`, `counter`. |
| `glosses` | 1–3 short English meanings, most common first. The first one appears in the placement toast, so keep it under ~20 characters. |
| `jlpt` | 5 for N5 … 1 for N1, or 0 when you don't know or it isn't on the JLPT lists. Journey boards only use words tagged for their band, so untagged words appear in themes only. |

Romaji is generated automatically (modified Hepburn with macrons: ぎゅうにゅう → gyūnyū). The build can't tell a
long vowel from two morphemes (思う is *omou*, not *omō*), so if a romaji comes out wrong, add a line to
`content/romaji_overrides.yaml`:

```yaml
思う: omou
```

**Gloss rules**

- Describe the word, never its category: `milk`, not `milk (a drink)`; `(my) father`, not `family: father`.
- Mark humble/in-group words the way learners need them: 父 is `(my) father`, お父さん would be `(someone's) father`.
- No trailing punctuation, no "to" prefixes on nouns.

## Writing categories (`content/categories.yaml`)

```yaml
- id: nomimono
  type: meaning
  label: "飲[の]み物[もの]"
  label_en: drinks
  rule_en: Things you drink
  min_level: 5
  members: [水, お茶, コーヒー, 牛乳, お酒, ジュース]
  excludes: []
  near_miss:
    牛乳: "belongs with 飲み物; it contains 牛 (cow) but it's something you drink"
```

| Field | Rules |
| --- | --- |
| `id` | Short, lower case, romaji, unique. Never change a published id. |
| `type` | `meaning` (semantic group), `script` (katakana loanwords vs native), `shared_kanji` (all contain one kanji), `counter` (nouns counted with one counter), `reading` (kanji read one way). |
| `label` | The Japanese label on the card, with furigana brackets. Keep it to 1–3 characters so it fits the tab above a foundation. |
| `label_en` | One or two English words, under ~12 characters: it sits in the corner of a small card. |
| `rule_en` | One line explaining the grouping. Shown when the player long-presses the category card. |
| `min_level` | The easiest journey band the category may appear at: `5` = from N5 up, `4` = from N4 up. Use `themed` for categories that only belong in themes; the journey never deals them. |
| `members` | Headwords from `words.yaml`. |
| `excludes` | Category ids that must never share a board with this one (see below). |
| `near_miss` | Optional, per member: the note shown if the player drops that word on the wrong foundation. |

### What makes a good category

- **One right answer.** A learner at that level should be able to decide membership from the word alone. If
  you have to argue for it, it's too loose.
- **Enough members at its level.** Boards deal 4–5 words per category at N5 and 5–6 at N4, and only from words
  inside the level's JLPT range. The build warns when a category can't be dealt:
  ```
  warning: den can't be dealt at N4: 3 members in range, needs 5
  ```
  Aim for 6–8 members in range, so boards vary.
- **Short headwords.** Cards are small, and long words shrink to fit (電子レンジ is about the limit). Prefer
  words of 1–4 characters.
- **Mixed difficulty inside the level**, so every board has an easy way in.

### Words that fit two categories

A word can be listed in more than one category (電車 is in both 乗り物 *vehicles* and 電 *electricity*). That's
fine: when both categories land on the same board, the generator leaves the ambiguous word out.

Use `excludes` when two categories overlap so much that sharing a board would be unfair even after that. The
usual case is a `script` category (外来語 · loanwords) next to a `meaning` category full of katakana words:

```yaml
- id: gairaigo
  type: script
  ...
  excludes: [nomimono, norimono]
```

Words that could plausibly be *mistaken* for another category are good, not bad: that's the puzzle. Give them a
`near_miss` note that teaches the difference. Write it as "belongs with X; why", in under ~70 characters.

## Writing a theme (`content/themes.yaml`)

A theme is a situation a learner will actually be in. Write the words they'll really hear and need there:
a doctor's theme wants 保険証, 問診票 and 処方箋, not textbook-generic words.

```yaml
- id: byouin
  title: "病[びょう]院[いん]に行[い]く"
  title_en: Going to the doctor
  blurb_en: The front desk, your symptoms, the exam and the pharmacy.
  categories: [uketsuke, shoujou, shinsatsu, yakkyoku, karada]
  foundations: 4
  columns: [2, 3, 4, 5, 6]
  slack: 2.0
  daily: true
```

| Field | Rules |
| --- | --- |
| `id` | Short, lower case, never changed once published. |
| `title` / `title_en` | Japanese title with furigana brackets, and its English title for the theme card. |
| `blurb_en` | One line under the title, ~60 characters. |
| `categories` | 3–5 category ids. Mostly `themed` categories (6 words each works well), and journey categories can join in: the doctor theme reuses 体 (body). |
| `foundations` | Slots on the board; must be fewer than the categories. |
| `columns` | Cards dealt into each column, left to right; the rest go to the draw pile. 4 columns for 3–4 categories, 5 for 5. |
| `slack` | How generous the move limit is: the solver's winning line × slack. 2.0 is relaxed, 1.6 is tight. |
| `daily` | `true` puts the theme in the daily challenge rotation. |

Every word in the theme's categories is dealt, so check the card count: 5 categories × (6 words + 1 category card)
is 35 cards, about the most a phone board holds comfortably. Near-misses are especially good in themes: 体温
(body temperature) contains 体 and could be mistaken for the body category, so it gets a `near_miss` note.

## Tuning the journey (`content/levels.yaml`)

Each entry sets the board from level `from` until the next entry; the last entry repeats forever.

```yaml
- from: 16
  band: 5
  categories: 4
  foundations: 3
  columns: [2, 3, 4, 5]
  words_per_category: [4, 5]
  slack: 2.0
```

| Field | Rules |
| --- | --- |
| `band` | JLPT band: 5 uses N5 words; 4 uses N5–N4; 3 uses N5–N3; 2 uses N4–N2; 1 uses N3–N1. |
| `categories` / `foundations` | Categories dealt, and slots to sort them into (fewer slots than categories). |
| `columns`, `slack` | As for themes. |
| `words_per_category` | `[min, max]` word cards per category. Every category allowed at the band needs at least `min` words in range, or the build warns. |

Make the curve rise in steps: tighten `slack` or add a category, not both at once, and move up a band only after a
long stretch at the current one. Changes reach players from their next level.

## Publishing

```sh
uv run tools/build.py        # validate and write docs/v1/
git add content docs
git commit -m "Add 家 category (house and home)"
git push
```

- **Errors** (a member that isn't in `words.yaml`, a malformed furigana, 0 or 4+ glosses) stop the build.
  Nothing is written until they're fixed.
- **Warnings** (a category that can't be dealt) still build, but that category won't appear in the game.
- The content version bumps automatically whenever the output changes. Always commit `docs/` together with the
  YAML change.
- GitHub Pages serves the new JSON within about a minute. Installed apps download it on their next launch and
  use it from the next board they deal; a board in progress is never changed.
- Each app release also bundles a copy of the content for offline play, so tell engineering when a big content
  drop lands and they'll refresh the snapshot.

## Rules of the road

- **Don't change the JSON shape.** Adding words and categories is always safe. New fields or renamed fields
  need an app update first; talk to engineering. Breaking changes go to a new `docs/v2/` folder so older
  installs keep working.
- **Don't delete or rename published ids** (headwords, category ids, theme ids). The daily challenge and themes
  refer to them. To retire a word, remove it from its categories and leave it in `words.yaml`.
- **Write your own glosses.** Don't paste definitions from commercial dictionaries or textbooks. Dictionary
  data will come from JMdict (EDRDG, CC BY-SA 4.0) through the build, with attribution in the app.

## Checklist for a new theme

- [ ] Words a learner would really hear in that situation, each in `words.yaml` (`jlpt: 0` if untagged)
- [ ] 3–5 categories of about 6 words, `min_level: themed` unless they also suit the journey
- [ ] No word fits two of the theme's categories (or you're happy for the generator to leave it out)
- [ ] `near_miss` notes for words that look like they belong elsewhere
- [ ] `foundations` below the category count; `columns` sized for the card count
- [ ] `uv run tools/build.py` passes

## Checklist for a new category

- [ ] Every member is in `words.yaml` with furigana (if it has kanji), 1–3 glosses and a JLPT level
- [ ] No gloss names or hints at the category
- [ ] At least 6 members inside the category's level range, and no build warning for it
- [ ] Label ≤ 3 characters, `label_en` ≤ ~12 characters, one-line `rule_en`
- [ ] Overlaps with other categories are either acceptable (generator drops the word) or handled with `excludes`
- [ ] `near_miss` notes for the words players will most likely misplace
- [ ] `uv run tools/build.py` passes, and `docs/` is committed with the change
