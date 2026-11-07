#!/usr/bin/env python3
"""Build the translated pages of simface.com from the English index.html.

    python3 _tools/build_languages.py            # build /zh-cn/, /es/, ... and report missing translations
    python3 _tools/build_languages.py --strings  # write _i18n/_english-strings.json (every string that needs translating)

How it works
------------
* index.html (English) is the only page you edit by hand.
* _i18n/<lang>.json maps each English string to its translation: { "Play Now": "立即游戏", ... }
* Running this script writes <lang>/index.html for every language.
* Any English string without a translation is reported and left in English on that page.
Folders starting with "_" are not published by GitHub Pages.
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://www.simface.com"

# code -> (folder, html lang, hreflang/og locale, picker label, Google Play hl, rtl)
LANGS = {
    "zh-cn": ("zh-cn", "zh-Hans", "zh_CN", "中文", "zh_CN", False),
    "es":    ("es",    "es",      "es_ES", "ES",   "es",    False),
    "pt":    ("pt",    "pt",      "pt_BR", "PT",   "pt_BR", False),
    "fr":    ("fr",    "fr",      "fr_FR", "FR",   "fr",    False),
    "ar":    ("ar",    "ar",      "ar_AR", "عربي", "ar",    True),
    "id":    ("id",    "id",      "id_ID", "ID",   "id",    False),
    "ja":    ("ja",    "ja",      "ja_JP", "日本語", "ja",    False),
}

# Strings that stay the same in every language (names, handles, store names).
KEEP = {
    "SOCCER SUPERSTAR", "Soccer Superstar", "Real Freestyle Soccer", "Facebook", "Instagram", "TikTok",
    "Google Play", "App Store", "English", "简体中文", "Español", "Português", "Français", "العربية",
    "Bahasa Indonesia", "日本語", "EN", "Soccer Superstar:",
}

TOKEN = re.compile(r"<!--.*?-->|<(script|style|svg)\b.*?</\1\s*>|<[^>]+>|[^<]+", re.S | re.I)
ATTRS = re.compile(r'\b(alt|aria-label|data-ended-label|placeholder|title)="([^"]*)"')
META = re.compile(r'(<meta\s+(?:name|property)="(?:description|og:title|og:description|twitter:title|twitter:description|og:image:alt|twitter:image:alt)"\s+content=")([^"]*)(")')
TITLE = re.compile(r"(<title>)(.*?)(</title>)", re.S)
LDJSON = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)
MODALS = re.compile(r"\s*<!-- ═══ PRIVACY POLICY MODAL ═══ -->.*?(?=\n\s*<script>)", re.S)

LD_TEXT_FIELDS = {("WebSite", "name"), ("WebSite", "description"), ("VideoGame", "description"),
                  ("Question", "name"), ("Answer", "text")}


def norm(s):
    return " ".join(html.unescape(s).split())


def translatable(s):
    return (bool(re.search(r"[A-Za-z]", s)) and s not in KEEP
            and not re.fullmatch(r"[\w.+-]+@[\w.-]+|@\w+", s)          # emails, handles
            and not re.fullmatch(r"[\d.,]+[KMB]\+?", s)                  # 100M+, 53.3K
            and not re.fullmatch(r"[A-Z][a-z]+ [A-Z]\.", s))              # reviewer names like "Marcus T."


class Translator:
    def __init__(self, table):
        self.table = table
        self.missing = []
        self.seen = []

    def __call__(self, english):
        key = norm(english)
        if not translatable(key):
            return None
        if key not in self.seen:
            self.seen.append(key)
        if key in self.table:
            return self.table[key]
        if key not in self.missing:
            self.missing.append(key)
        return None


def translate_body(src, t):
    out = []
    for m in TOKEN.finditer(src):
        tok = m.group(0)
        if tok.startswith("<!--") or m.group(1):
            out.append(tok)
        elif tok.startswith("<"):
            def attr(a):
                tr = t(a.group(2))
                return a.group(0) if tr is None else f'{a.group(1)}="{html.escape(tr, quote=True)}"'
            out.append(ATTRS.sub(attr, tok))
        else:
            core = tok.strip()
            tr = t(core) if core else None
            if tr is None:
                out.append(tok)
            else:
                lead = tok[: len(tok) - len(tok.lstrip())]
                trail = tok[len(tok.rstrip()):]
                out.append(lead + html.escape(tr, quote=False) + trail)
    return "".join(out)


def translate_ld(block, t, url, lang):
    data = json.loads(block)

    def walk(node, typ=None):
        if isinstance(node, dict):
            types = node.get("@type")
            types = types if isinstance(types, list) else [types]
            here = next((x for x in types if x), typ)
            for k, v in node.items():
                if isinstance(v, str) and any((ty, k) in LD_TEXT_FIELDS for ty in types):
                    tr = t(v)
                    if tr is not None:
                        node[k] = tr
                elif k in ("url", "mainEntityOfPage") and v == SITE + "/" and here in ("WebSite", "VideoGame"):
                    node[k] = url
                elif k == "inLanguage":
                    node[k] = lang
                else:
                    walk(v, here)
        elif isinstance(node, list):
            for x in node:
                walk(x, typ)

    walk(data)
    body = json.dumps(data, ensure_ascii=False, indent=2)
    return "\n  " + body.replace("\n", "\n  ") + "\n  "


def build(src, code, table):
    folder, lang, locale, label, hl, rtl = LANGS[code]
    url = f"{SITE}/{folder}/"
    t = Translator(table)
    page = src

    page = page.replace('<html lang="en">', f'<html lang="{lang}"' + (' dir="rtl"' if rtl else "") + ">", 1)
    page = TITLE.sub(lambda m: m.group(1) + html.escape(t(m.group(2)) or m.group(2), quote=False) + m.group(3), page, 1)
    page = META.sub(lambda m: m.group(1) + html.escape(t(m.group(2)) or html.unescape(m.group(2)), quote=True) + m.group(3), page)
    page = page.replace(f'<link rel="canonical" href="{SITE}/">', f'<link rel="canonical" href="{url}">', 1)
    page = page.replace(f'<meta property="og:url" content="{SITE}/">', f'<meta property="og:url" content="{url}">', 1)
    page = page.replace('<meta property="og:locale" content="en_US">', f'<meta property="og:locale" content="{locale}">', 1)
    page = page.replace(f'<meta property="og:locale:alternate" content="{locale}">', '<meta property="og:locale:alternate" content="en_US">', 1)
    page = LDJSON.sub(lambda m: m.group(1) + translate_ld(m.group(2), t, url, lang) + m.group(3), page, 1)

    page = MODALS.sub("", page, 1)  # English-only legal pop-ups are not needed on translated pages
    start, end = page.index("<body>"), page.rindex("<script>")
    page = page[:start] + translate_body(page[start:end], t) + page[end:]

    # Language picker: show the current language
    page = page.replace('<span class="lang-current">EN</span>', f'<span class="lang-current">{label}</span>', 1)
    page = page.replace(f'data-lang="{code}">', f'data-lang="{code}" aria-current="true">', 1)
    # Google Play listing in the visitor's language
    page = page.replace("hl=en_US", f"hl={hl}")
    return page, t


def main():
    src = (ROOT / "index.html").read_text(encoding="utf-8")
    if "--strings" in sys.argv:
        _, t = build(src, "es", {})  # an empty table reports every translatable string as missing
        out = ROOT / "_i18n" / "_english-strings.json"
        out.write_text(json.dumps(t.missing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{len(t.missing)} strings -> {out.relative_to(ROOT)}")
        return

    # English page: mark English as current in the picker
    en = src.replace('data-lang="en">', 'data-lang="en" aria-current="true">', 1) if 'data-lang="en" aria-current' not in src else src
    if en != src:
        (ROOT / "index.html").write_text(en, encoding="utf-8")
        src = en

    problems = 0
    for code in LANGS:
        path = ROOT / "_i18n" / f"{code}.json"
        table = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        page, t = build(src, code, table)
        page = page.replace('data-lang="en" aria-current="true">', 'data-lang="en">', 1)
        dest = ROOT / LANGS[code][0] / "index.html"
        dest.parent.mkdir(exist_ok=True)
        dest.write_text(page, encoding="utf-8")
        unused = [k for k in table if k not in t.seen]
        status = "ok" if not t.missing else f"{len(t.missing)} missing"
        print(f"{code:6} {status:12} -> {dest.relative_to(ROOT)}" + (f"   ({len(unused)} unused entries)" if unused else ""))
        for s in t.missing:
            problems += 1
            print(f"         missing: {s[:90]}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
