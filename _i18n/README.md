# Translations

The site is published in 8 languages. **English `index.html` is the only page you edit by hand.**
Every other language page (`/zh-cn/`, `/es/`, `/pt/`, `/fr/`, `/ar/`, `/id/`, `/ja/`) is generated from it.

Each file here (`zh-cn.json`, `es.json`, …) maps an English sentence on the page to its translation.

## After changing text on the English page

1. Add the new English text and its translation to every language file.
2. Run `python3 _tools/build_languages.py`.
   It rebuilds all language pages and lists any English text that is still missing a translation
   (missing text stays in English on that page until it's added).
3. Commit the updated `index.html`, the `_i18n/*.json` files and the rebuilt language folders.

`_english-strings.json` lists every English string on the page (`python3 _tools/build_languages.py --strings` refreshes it).
