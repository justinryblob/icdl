#!/usr/bin/env python3
"""
Static site builder for "Introducing Chemistry on a Deeper Level".

    python3 build.py            # writes the finished site to ./dist

No third-party packages are needed. Cloudflare Pages settings if you connect a repo:
    Build command:           python3 build.py
    Build output directory:  dist

Content lives in  content/  as small Markdown files, and the order of units,
chapters and lessons lives in  book.json.  See README.md for how to add more.
"""
import hashlib
import html
import json
import re
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
STATIC = ROOT / "static"
DIST = ROOT / "dist"

BOOK = json.loads((ROOT / "book.json").read_text(encoding="utf-8"))
SITE_TITLE = BOOK["title"]


# --------------------------------------------------------------------------
# Markdown (a small, predictable subset)
#   paragraphs, ### subheadings, 1. ordered lists, - bullet lists,
#   **bold**, *italic*, and figures:  ![alt text](images/file.png "Caption")
# --------------------------------------------------------------------------

def esc(s):
    return html.escape(s, quote=True)


def inline(s):
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    return s


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


IMG_RE = re.compile(r'^!\[(?P<alt>.*?)\]\((?P<src>\S+?)(?: "(?P<cap>.*)")?\)$')


def figure(alt, src, cap, prefix):
    size = png_size(STATIC / src)
    if size is None:
        sys.exit(f"Image not found or not a PNG: static/{src}")
    w, h = size
    img = (
        f'<img src="{prefix}{esc(src)}" alt="{esc(alt)}" width="{w}" height="{h}" '
        f'style="--w:{w}" loading="lazy" decoding="async">'
    )
    if cap:
        return f'<figure class="fig">{img}<figcaption>{inline(cap)}</figcaption></figure>'
    return f'<figure class="fig bare">{img}</figure>'


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def markdown(text, prefix):
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [l.rstrip() for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        first = lines[0]
        m = IMG_RE.match(first) if len(lines) == 1 else None
        if m:
            out.append(figure(m["alt"], m["src"], m["cap"], prefix))
        elif first.startswith("### "):
            title = first[4:].strip()
            out.append(f'<h3 id="{slugify(title)}">{inline(title)}</h3>')
        elif all(re.match(r"\d+\.\s", l) for l in lines):
            start = int(re.match(r"(\d+)\.", first).group(1))
            items = "".join(f"<li>{inline(re.sub(r'^\d+\.\s+', '', l))}</li>" for l in lines)
            attr = f' start="{start}"' if start != 1 else ""
            out.append(f"<ol{attr}>{items}</ol>")
        elif all(l.startswith("- ") for l in lines):
            items = "".join(f"<li>{inline(l[2:])}</li>" for l in lines)
            out.append(f"<ul>{items}</ul>")
        else:
            out.append(f"<p>{inline(' '.join(lines))}</p>")
    return "\n".join(out)


def first_sentence_text(md, limit=155):
    for block in re.split(r"\n\s*\n", md.strip()):
        if block.startswith(("!", "#", "1.", "- ")):
            continue
        t = re.sub(r"\*+", "", " ".join(block.split()))
        return t if len(t) <= limit else t[: limit - 1].rsplit(" ", 1)[0] + "…"
    return ""


# --------------------------------------------------------------------------
# Book model
# --------------------------------------------------------------------------

def build_model():
    pages = []  # reading order: unit intros + lessons that have a file
    for u in BOOK["units"]:
        u["href"] = f'{u["slug"]}/'
        u["page"] = {
            "kind": "unit", "unit": u, "title": u["title"],
            "eyebrow": f'Unit {u["id"]}', "path": u["href"],
            "file": u.get("intro"), "label": f'Unit {u["id"]}: {u["title"]}',
        }
        pages.append(u["page"])
        for c in u["chapters"]:
            c["unit"] = u
            for l in c["lessons"]:
                l["chapter"], l["unit"] = c, u
                l["slug"] = l["id"].replace(".", "-")
                l["href"] = f'{u["slug"]}/{l["slug"]}/' if l.get("file") else None
                if l.get("file"):
                    single = len(c["lessons"]) == 1
                    l["page"] = {
                        "kind": "lesson", "lesson": l, "unit": u, "chapter": c,
                        "title": l["title"], "path": l["href"], "file": l["file"],
                        "single": single,
                        "label": f'{l["id"]} {l["title"]}',
                    }
                    pages.append(l["page"])
    for i, p in enumerate(pages):
        p["prev"] = pages[i - 1] if i else None
        p["next"] = pages[i + 1] if i + 1 < len(pages) else None
    return pages


# --------------------------------------------------------------------------
# HTML templates
# --------------------------------------------------------------------------

THEME_BOOT = (
    "<script>try{var t=localStorage.getItem('icdl-theme');"
    "if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t)}catch(e){}</script>"
)

ICON_MENU = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>'
ICON_MOON = '<svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>'
ICON_SUN = '<svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>'


def sidebar(prefix, current):
    cu = current["unit"] if current and current["kind"] in ("unit", "lesson") else None
    cc = current.get("chapter") if current else None
    parts = [
        f'<a class="brand" href="{prefix}" aria-label="{esc(SITE_TITLE)} — home">'
        f'<img src="{prefix}logo.png" alt="{esc(SITE_TITLE)}" width="1262" height="426"></a>',
        '<nav aria-label="Table of contents"><ul class="units">',
    ]
    for u in BOOK["units"]:
        open_u = " open" if u is cu else ""
        ov_cur = ' aria-current="page"' if current and current is u["page"] else ""
        parts.append(
            f'<li><details class="unit"{open_u}><summary><span class="num">Unit {esc(u["id"])}</span>'
            f'<span>{esc(u["title"])}</span></summary><div class="unit-body"><ul>'
            f'<li><a class="overview" href="{prefix}{u["href"]}"{ov_cur}>Overview</a></li>'
        )
        for c in u["chapters"]:
            if len(c["lessons"]) == 1:
                l = c["lessons"][0]
                if l.get("href"):
                    cur = ' aria-current="page"' if current and current is l["page"] else ""
                    parts.append(
                        f'<li class="chapter-single"><a href="{prefix}{l["href"]}"{cur}>'
                        f'<span class="num">{esc(c["id"])}</span><span>{esc(c["title"])}</span></a></li>'
                    )
                else:
                    parts.append(
                        f'<li class="chapter-single"><span class="soon" title="Coming soon">'
                        f'<span class="num">{esc(c["id"])}</span><span>{esc(c["title"])}</span></span></li>'
                    )
                continue
            open_c = " open" if c is cc else ""
            parts.append(
                f'<li><details class="chapter"{open_c}><summary><span class="num">{esc(c["id"])}</span>'
                f'<span>{esc(c["title"])}</span></summary><ul class="lessons">'
            )
            for l in c["lessons"]:
                label = f'<span class="num">{esc(l["id"])}</span><span>{esc(l["title"])}</span>'
                if l.get("href"):
                    cur = ' aria-current="page"' if current and current is l["page"] else ""
                    parts.append(f'<li><a href="{prefix}{l["href"]}"{cur}>{label}</a></li>')
                else:
                    parts.append(f'<li><span class="soon" title="Coming soon">{label}</span></li>')
            parts.append("</ul></details></li>")
        parts.append("</ul></div></details></li>")
    parts.append("</ul></nav>")
    return "".join(parts)


def contents_block(prefix, unit, heading="Lesson plan"):
    rows = [f'<section class="contents" aria-label="{esc(heading)}"><h2>{esc(heading)}</h2><ol>']
    for c in unit["chapters"]:
        single = len(c["lessons"]) == 1
        if single:
            l = c["lessons"][0]
            if l.get("href"):
                title = f'<a href="{prefix}{l["href"]}">{esc(c["title"])}</a>'
            else:
                title = f'<span class="soon">{esc(c["title"])}</span><span class="tag">Soon</span>'
            rows.append(f'<li><div class="ch"><span class="num">{esc(c["id"])}</span><span>{title}</span></div></li>')
            continue
        rows.append(f'<li><div class="ch"><span class="num">{esc(c["id"])}</span><span>{esc(c["title"])}</span></div><ol>')
        for l in c["lessons"]:
            if l.get("href"):
                t = f'<a href="{prefix}{l["href"]}">{esc(l["title"])}</a>'
            else:
                t = f'<span class="soon">{esc(l["title"])}</span><span class="tag">Soon</span>'
            rows.append(f'<li><span class="num">{esc(l["id"])}</span><span>{t}</span></li>')
        rows.append("</ol></li>")
    rows.append("</ol></section>")
    return "".join(rows)


def pager(prefix, page):
    def cell(p, cls, label):
        if not p:
            return ""
        return (f'<a class="{cls}" href="{prefix}{p["path"]}" rel="{ "prev" if cls=="prev" else "next"}">'
                f'<span class="dir">{label}</span><span class="t">{esc(p["label"])}</span></a>')
    return (f'<nav class="pager" aria-label="Previous and next lesson">'
            f'{cell(page["prev"], "prev", "Previous")}{cell(page["next"], "next", "Next")}</nav>')


def shell(prefix, title, desc, body, current=None, home=False, asset_v=None):
    cls = ' class="home"' if home else ""
    v = asset_v
    side = "" if home else f'<aside class="sidebar" id="toc">{sidebar(prefix, current)}</aside><div class="scrim"></div>'
    menu = ("" if home else
            f'<button class="icon-btn" id="nav-toggle" type="button" aria-controls="toc" aria-expanded="false" '
            f'aria-label="Open contents">{ICON_MENU}</button>')
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="theme-color" content="#fcfbf8" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#131417" media="(prefers-color-scheme: dark)">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<link rel="icon" href="{prefix}favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="{prefix}favicon-32.png">
<link rel="apple-touch-icon" href="{prefix}apple-touch-icon.png">
{THEME_BOOT}
<link rel="stylesheet" href="{prefix}style.css?v={v['css']}">
</head>
<body{cls}>
<a class="skip" href="#content">Skip to content</a>
<div class="layout">
{side}
<div class="main-wrap">
<header class="topbar">{menu}<span class="spacer"></span>
<button class="icon-btn" id="theme-toggle" type="button" aria-label="Switch to dark mode" title="Switch to dark mode">{ICON_MOON}{ICON_SUN}</button>
</header>
<main id="content">
{body}
</main>
</div>
</div>
<script src="{prefix}site.js?v={v['js']}" defer></script>
</body>
</html>
"""


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------

def write(rel, text):
    p = DIST / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def short_hash(path):
    return hashlib.md5(path.read_bytes()).hexdigest()[:8]


def main():
    pages = build_model()
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(STATIC, DIST)

    v = {"css": short_hash(STATIC / "style.css"), "js": short_hash(STATIC / "site.js")}
    problems = []

    for p in pages:
        depth = p["path"].count("/")
        prefix = "../" * depth
        md = ""
        if p["file"] and (CONTENT / p["file"]).exists():
            md = (CONTENT / p["file"]).read_text(encoding="utf-8")
        elif p["file"]:
            problems.append(f'missing content file: content/{p["file"]}')
        body_html = markdown(md, prefix) if md else ""

        if p["kind"] == "unit":
            u = p["unit"]
            head = (f'<div class="eyebrow">Unit {esc(u["id"])}</div><h1>{esc(u["title"])}</h1><hr class="title-rule">')
            body = f'<article>{head}{body_html}{contents_block(prefix, u)}{pager(prefix, p)}</article>'
            title = f'Unit {u["id"]}: {u["title"]} — {SITE_TITLE}'
        else:
            l, c, u = p["lesson"], p["chapter"], p["unit"]
            if p["single"]:
                eyebrow = f'<span>{esc(l["id"])}</span>'
            else:
                eyebrow = f'<span>{esc(l["id"])}</span><span class="sep">·</span><span>{esc(c["title"])}</span>'
            head = f'<div class="eyebrow">{eyebrow}</div><h1>{esc(l["title"])}</h1><hr class="title-rule">'
            body = f'<article>{head}{body_html}{pager(prefix, p)}</article>'
            title = f'{l["id"]} {l["title"]} — {SITE_TITLE}'
        desc = first_sentence_text(md) or SITE_TITLE
        write(p["path"] + "index.html", shell(prefix, title, desc, body, current=p, asset_v=v))

    # Home
    intro = ""
    cards = []
    first = pages[0]
    for u in BOOK["units"]:
        cards.append(contents_block("", u, f'Unit {u["id"]} · {u["title"]}'))
    home_body = (
        '<article><div class="hero">'
        f'<img src="logo.png" alt="{esc(SITE_TITLE)}" width="1262" height="426">'
        f'<p>Start with Unit 1: {esc(BOOK["units"][0]["title"])}</p>'
        f'<a class="btn" href="{first["path"]}">Start reading</a></div>'
        + "".join(cards) + "</article>"
    )
    write("index.html", shell("", SITE_TITLE, "A digital study guide to chemistry, built from the ground up: atoms, orbitals, bonding and beyond.", home_body, home=True, asset_v=v))

    # 404 (absolute paths, since it is served at any URL)
    nf = ('<article><div class="eyebrow">404</div><h1>Page not found</h1><hr class="title-rule">'
          '<p>That page doesn’t exist (yet). <a href="/">Head back to the start</a>.</p></article>')
    write("404.html", shell("/", "Page not found — " + SITE_TITLE, "Page not found", nf, home=True, asset_v=v))

    write("_headers",
          "/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n\n"
          "/style.css\n  Cache-Control: public, max-age=31536000, immutable\n\n"
          "/site.js\n  Cache-Control: public, max-age=31536000, immutable\n\n"
          "/images/*\n  Cache-Control: public, max-age=86400\n")
    write("robots.txt", "User-agent: *\nAllow: /\n")

    # Sanity checks
    for html_file in DIST.rglob("*.html"):
        text = html_file.read_text(encoding="utf-8")
        for m in re.finditer(r'(?:src|href)="((?:\.\./)*[^"#:?]+?)(?:\?[^"]*)?"', text):
            ref = m.group(1)
            if ref.startswith("/") or ref.startswith("mailto"):
                continue
            target = (html_file.parent / ref).resolve()
            if target.is_dir():
                target = target / "index.html"
            if not target.exists():
                problems.append(f"{html_file.relative_to(DIST)}: broken link {ref}")
    used = {m for f in DIST.rglob("*.html") for m in re.findall(r'images/([^"]+)"', f.read_text(encoding="utf-8"))}
    for img in sorted((STATIC / "images").glob("*")):
        if img.name not in used:
            problems.append(f"image never used: static/images/{img.name}")

    n = len(pages)
    print(f"Built {n} pages into {DIST.relative_to(ROOT)}/")
    if problems:
        print("\nWarnings:")
        for pr in problems:
            print("  -", pr)


if __name__ == "__main__":
    main()
