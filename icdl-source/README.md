# Introducing Chemistry on a Deeper Level: site source

## Deploy (no build needed)
Upload the contents of `dist/` (or the separate `icdl-site.zip`) to Cloudflare Pages
via Workers & Pages > Create > Pages > Upload assets.

## Or connect a Git repo
Build command: `python3 build.py`   Build output directory: `dist`

## Preview locally
    python3 build.py
    cd dist && python3 -m http.server 8000     # then open http://localhost:8000

## Add a lesson
1. Create `content/unit-1/1-2-3.md` (plain text with a little Markdown).
2. In `book.json`, add `"file": "unit-1/1-2-3.md"` to that lesson. Lessons without a `file` show as "Soon".
3. Run `python3 build.py` and re-upload.

## Add a unit
Copy a unit block in `book.json`, give it a new `slug` (e.g. `unit-2`), add its `content/unit-2/` files, rebuild.

## Markdown supported
Paragraphs, `### Subheading`, `1.` lists, `- ` lists, `**bold**`, `*italic*`, and figures:
`![alt text](images/file.png "Caption")` (put the image in `static/images/`).

## Images
Originals are used untouched. In dark mode they are colour-inverted by CSS only (see `--img-filter` in `static/style.css`).
