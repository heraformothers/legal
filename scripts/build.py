#!/usr/bin/env python3
"""Build the Hera legal pages from the Markdown sources in source/.

Deliberately dependency-free: no Markdown library, no template engine, no
third-party fonts, no JavaScript. A legal site should be inspectable end to end,
and the output should be identical on any machine.

Handles exactly the Markdown subset the documents use:
  headings, horizontal rules, paragraphs, unordered lists, blockquotes,
  pipe tables, links, bold, italics, inline code.

Run:  python3 scripts/build.py
"""

from __future__ import annotations

import html
import pathlib
import re
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / "source"

# route -> (source file, <title>, index blurb)
PAGES = {
    "privacy": ("PRIVACY_NOTICE.md", "Privacy Notice", "What Hera collects, why, who can reach it, and how to have it deleted."),
    "terms": ("TERMS_OF_USE.md", "Terms of Use", "The agreement between you and Hera, including what Hera is and is not."),
    "community-guidelines": ("COMMUNITY_GUIDELINES.md", "Community Guidelines", "The rules for the Circle, and what happens when one is broken."),
    "mentor-agreement": ("MENTOR_AGREEMENT.md", "Mentor Agreement", "Confidentiality, boundaries and conduct for volunteer peer mentors."),
}

DRAFT_BANNER = """<div class="draft-banner" role="note">
  DRAFT FOR REVIEW &mdash; NOT YET EFFECTIVE
  <p>This document is published for review only. It is not in force, some details are still
  unresolved, and it must not be relied on.</p>
</div>"""

SUPPORT_EMAIL = "heraformothers@gmail.com"


# --------------------------------------------------------------- inline pass

def slugify(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"^\d+[.)]\s*", "", text.strip())
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"\s+", "-", text).strip("-")


def inline(text: str) -> str:
    """Escape, then re-introduce the small set of inline constructs we allow."""
    out = html.escape(text, quote=False)

    # Links first, so their bracket syntax is not mistaken for a placeholder.
    out = re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)\)",
        lambda m: f'<a href="{html.escape(m.group(2), quote=True)}">{m.group(1)}</a>',
        out,
    )

    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?![*\w])", r"<em>\1</em>", out)

    # Unresolved publication details stay VISIBLE and clearly marked. Section 4
    # of the authorisation: do not conceal them, do not invent values.
    out = re.sub(
        r"\[([A-Z][^\]]*)\]",
        lambda m: f'<span class="placeholder">[{m.group(1)}]</span>',
        out,
    )
    return out


# ---------------------------------------------------------------- block pass

def render_table(rows: list[str]) -> str:
    cells = [[c.strip() for c in row.strip().strip("|").split("|")] for row in rows]
    header, body = cells[0], cells[2:]  # cells[1] is the --- separator
    head_html = "".join(f"<th scope=\"col\">{inline(h)}</th>" for h in header)

    body_html = []
    for row in body:
        tds = []
        for index, cell in enumerate(row):
            label = header[index] if index < len(header) else ""
            # data-label drives the stacked card layout on narrow screens.
            tds.append(f'<td data-label="{html.escape(label, quote=True)}">{inline(cell)}</td>')
        body_html.append("<tr>" + "".join(tds) + "</tr>")

    return (
        '<div class="tablewrap"><table>\n<thead><tr>'
        + head_html
        + "</tr></thead>\n<tbody>\n"
        + "\n".join(body_html)
        + "\n</tbody>\n</table></div>"
    )


def render(markdown: str) -> tuple[str, str]:
    """Returns (html_body, first_h1_text)."""
    lines = markdown.split("\n")
    out: list[str] = []
    title = ""
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            index += 1
            continue

        # Horizontal rule
        if re.fullmatch(r"-{3,}", stripped):
            out.append("<hr>")
            index += 1
            continue

        # Headings
        heading = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if heading:
            level = len(heading.group(1))
            text = heading.group(2).strip()
            if level == 1 and not title:
                title = re.sub(r"<[^>]+>", "", text)
                out.append(f"<h1>{inline(text)}</h1>")
            else:
                out.append(f'<h{level} id="{slugify(text)}">{inline(text)}</h{level}>')
            index += 1
            continue

        # Table
        if stripped.startswith("|") and index + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[index + 1].strip()):
            block = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                block.append(lines[index])
                index += 1
            out.append(render_table(block))
            continue

        # Blockquote -> review note
        if stripped.startswith(">"):
            block = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                block.append(re.sub(r"^\s*>\s?", "", lines[index]))
                index += 1
            joined = " ".join(part.strip() for part in block if part.strip())
            out.append(f'<div class="reviewnote"><p>{inline(joined)}</p></div>')
            continue

        # Unordered list
        if re.match(r"^[-*]\s+", stripped):
            items = []
            while index < len(lines) and re.match(r"^\s*[-*]\s+", lines[index]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[index]).strip())
                index += 1
            out.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>")
            continue

        # Ordered list
        if re.match(r"^\d+[.)]\s+", stripped):
            items = []
            while index < len(lines) and re.match(r"^\s*\d+[.)]\s+", lines[index]):
                items.append(re.sub(r"^\s*\d+[.)]\s+", "", lines[index]).strip())
                index += 1
            out.append("<ol>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ol>")
            continue

        # Paragraph
        block = []
        while index < len(lines) and lines[index].strip() and not re.match(
            r"^\s*(#{1,4}\s|[-*]\s|\d+[.)]\s|>|\|)", lines[index]
        ) and not re.fullmatch(r"-{3,}", lines[index].strip()):
            block.append(lines[index].strip())
            index += 1
        if block:
            out.append(f"<p>{inline(' '.join(block))}</p>")
        else:
            index += 1

    return "\n".join(out), title


# ------------------------------------------------------------------- layout

DOC_META = """<div class="docmeta"><dl>
<dt>Document</dt><dd>{title}</dd>
<dt>Version</dt><dd>{version}</dd>
<dt>Status</dt><dd>Draft for review &mdash; not yet effective</dd>
<dt>Effective date</dt><dd>Pending</dd>
</dl></div>"""


def inject_doc_meta(body: str, title: str, version: str) -> str:
    """Puts a structured version/status block directly under the <h1>."""
    marker = "</h1>"
    position = body.find(marker)
    if position == -1:
        return DOC_META.format(title=html.escape(title), version=version) + body
    position += len(marker)
    return body[:position] + "\n" + DOC_META.format(title=html.escape(title), version=version) + body[position:]


def page(title: str, body: str, *, back: bool = True, description: str = "") -> str:
    backlink = '<p class="backlink"><a href="../legal/">&larr; All Hera legal documents</a></p>' if back else ""
    return f"""<!DOCTYPE html>
<html lang="en-SG">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- Temporary while these pages are a draft for review. Remove when they go live. -->
<meta name="robots" content="noindex, nofollow">
<meta name="description" content="{html.escape(description or title, quote=True)}">
<title>{html.escape(title)} &middot; Hera</title>
<link rel="stylesheet" href="../assets/style.css">
</head>
<body>
{DRAFT_BANNER}
<main class="wrap">
{backlink}
{body}
<footer>
<p>Hera is an unincorporated, student-led project in Singapore providing non-clinical peer support.
It is not a medical or emergency service.</p>
<p>Questions, requests or complaints: <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a></p>
<p><a href="../legal/">All legal documents</a> &middot; <a href="../support/">Support</a></p>
</footer>
</main>
</body>
</html>
"""


def write(route: str, contents: str) -> None:
    directory = ROOT / route
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "index.html").write_text(contents, encoding="utf-8")
    print(f"  /{route}/")


def main() -> None:
    print("Building Hera legal pages...")

    for route, (filename, title, _blurb) in PAGES.items():
        markdown = (SOURCE / filename).read_text(encoding="utf-8")
        body, _ = render(markdown)
        version_match = re.search(r"Version\s+([0-9]{4}-[0-9]{2}-[0-9]{2}\.[0-9]+)", markdown)
        version = version_match.group(1) if version_match else "unversioned"
        body = inject_doc_meta(body, title, version)
        write(route, page(title, body, description=_blurb))

    # ------------------------------------------------------------- /legal/
    items = "".join(
        f'<li><a href="../{route}/">{title}</a><p>{blurb}</p></li>'
        for route, (_f, title, blurb) in PAGES.items()
    )
    legal_body = f"""<h1>Hera &mdash; legal documents</h1>
<div class="docmeta"><dl>
<dt>Document set</dt><dd>2026-08-05.1</dd>
<dt>Status</dt><dd>Draft for review &mdash; not yet effective</dd>
<dt>Effective date</dt><dd>Pending</dd>
</dl></div>
<p>These are the documents that govern using Hera. They are published here so they can be read
before creating an account, and without signing in.</p>
<ul class="doclist">{items}</ul>
<h2 id="contact">Contact</h2>
<p>Questions, requests or complaints: <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a>.
We aim to reply within 14 days. See also <a href="../support/">Support</a>.</p>"""
    write("legal", page("Legal", legal_body, back=False, description="Hera's Terms of Use, Privacy Notice, Community Guidelines and Mentor Agreement."))

    # ----------------------------------------------------------- /support/
    support_body = f"""<h1>Support</h1>
<div class="reviewnote"><p><strong>If you or someone else is in immediate danger, contact emergency
services directly. Do not rely on Hera.</strong> In Singapore: <strong>995</strong> for an
ambulance, <strong>999</strong> for the police.</p></div>
<p>Hera is an unincorporated, student-led project providing non-clinical peer support for pregnant
and postpartum mothers in Singapore. Hera is not a medical service and not an emergency service. No
one at Hera is monitoring the app for people in danger.</p>
<h2 id="contact-us">Contact us</h2>
<p>For help with the app, a privacy request, or a complaint, email
<a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a>. We aim to reply within 14 days.</p>
<div class="tablewrap"><table>
<thead><tr><th scope="col">What you need</th><th scope="col">Who to contact</th></tr></thead>
<tbody>
<tr><td data-label="What you need">General support or an account problem</td>
    <td data-label="Who to contact"><a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a></td></tr>
<tr><td data-label="What you need">Privacy, access or correction request</td>
    <td data-label="Who to contact"><span class="placeholder">[NAME OR &quot;Hera Data Protection Lead&quot;]</span>,
    at <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a></td></tr>
<tr><td data-label="What you need">Moderation or safety concern</td>
    <td data-label="Who to contact"><span class="placeholder">[FULL NAME OR ROLE &mdash; moderation and safety lead]</span>,
    at <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a></td></tr>
<tr><td data-label="What you need">Who is responsible for Hera</td>
    <td data-label="Who to contact"><span class="placeholder">[FULL LEGAL NAME]</span>, Hera Project Team</td></tr>
</tbody></table></div>
<h2 id="crisis-resources">Crisis resources in Singapore</h2>
<p>These are independent organisations. Hera does not control, endorse, or take responsibility for
the services they provide, and these numbers may change.</p>
<ul>
<li><strong>Emergency</strong> &mdash; Ambulance 995, Police 999</li>
<li><strong>National mindline</strong> (24/7 mental health support) &mdash; 1771</li>
<li><strong>NUH Women's Emotional Health Service</strong> &mdash; 6772 2037, Monday to Friday, 8am&ndash;5pm</li>
<li><strong>National Anti-Violence &amp; Sexual Harassment Helpline</strong> &mdash; 1800-777-0000</li>
</ul>
<h2 id="legal">Legal documents</h2>
<p>See <a href="../legal/">all Hera legal documents</a>.</p>"""
    write("support", page("Support", support_body, description="How to contact Hera, and crisis resources in Singapore."))

    # ------------------------------------------------------- / (forwarding)
    root_body = """<h1>Hera</h1>
<p>This site hosts Hera's legal documents and support information.</p>
<ul class="doclist">
<li><a href="./legal/">Legal documents</a><p>Terms of Use, Privacy Notice, Community Guidelines and Mentor Agreement.</p></li>
<li><a href="./support/">Support</a><p>How to reach us, and crisis resources.</p></li>
</ul>"""
    root_html = page("Hera", root_body, back=False, description="Hera legal documents and support.")
    # The root page is one level up from every other page, so fix its relative
    # links: ../assets -> ./assets, ../legal -> ./legal.
    root_html = root_html.replace('href="../assets/', 'href="./assets/')
    root_html = root_html.replace('href="../legal/', 'href="./legal/')
    root_html = root_html.replace('href="../support/', 'href="./support/')
    (ROOT / "index.html").write_text(root_html, encoding="utf-8")
    print("  /")

    # GitHub Pages: serve the files exactly as generated, no Jekyll processing.
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    print("Done.")


if __name__ == "__main__":
    main()
