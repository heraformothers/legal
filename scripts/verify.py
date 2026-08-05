#!/usr/bin/env python3
"""Local verification of the built legal site.

Checks the things that are cheap to get wrong and expensive to discover after
publication: broken internal links, missing draft banners, concealed
placeholders, and any request that would leave the visitor's browser.

Run:  python3 scripts/verify.py
Exits non-zero if anything fails.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ROUTES = ["legal", "privacy", "terms", "community-guidelines", "mentor-agreement", "support"]

failures: list[str] = []
notes: list[str] = []


def check(condition: bool, message: str) -> None:
    if condition:
        print(f"  PASS  {message}")
    else:
        print(f"  FAIL  {message}")
        failures.append(message)


print("Hera legal site verification\n")

# --------------------------------------------------------------- 1. routes
print("Routes")
pages: dict[str, str] = {}
for route in ROUTES:
    path = ROOT / route / "index.html"
    check(path.is_file(), f"/{route}/ exists")
    if path.is_file():
        pages[route] = path.read_text(encoding="utf-8")
check((ROOT / "index.html").is_file(), "/ exists")
pages["(root)"] = (ROOT / "index.html").read_text(encoding="utf-8")
check((ROOT / ".nojekyll").is_file(), ".nojekyll present (Pages serves files as-is)")

# ------------------------------------------------------- 2. required markup
print("\nPer-page requirements")
for name, source in pages.items():
    label = f"/{name}/" if name != "(root)" else "/"
    ok = 'class="draft-banner"' in source and "DRAFT FOR REVIEW" in source
    check(ok, f"{label} shows the draft banner")
    check('name="robots" content="noindex, nofollow"' in source, f"{label} is noindex")
    check("<title>" in source and "</title>" in source, f"{label} has a title")
    check(source.count("<h1") == 1, f"{label} has exactly one h1")
    check('lang="en-SG"' in source, f"{label} declares a language")
    check('name="viewport"' in source, f"{label} has a viewport meta")

# ------------------------------------------------- 3. heading order sanity
print("\nHeading order")
for name, source in pages.items():
    label = f"/{name}/" if name != "(root)" else "/"
    levels = [int(m) for m in re.findall(r"<h([1-4])[ >]", source)]
    jumps = [
        (levels[i], levels[i + 1])
        for i in range(len(levels) - 1)
        if levels[i + 1] - levels[i] > 1
    ]
    check(not jumps, f"{label} never skips a heading level {jumps if jumps else ''}")

# ------------------------------------------------------- 4. internal links
print("\nInternal links")
for name, source in pages.items():
    label = f"/{name}/" if name != "(root)" else "/"
    base = ROOT if name == "(root)" else ROOT / name
    for href in re.findall(r'href="([^"]+)"', source):
        if href.startswith(("mailto:", "http://", "https://", "#")):
            continue
        target = (base / href).resolve()
        if target.is_dir():
            target = target / "index.html"
        elif href.endswith("/"):
            target = target / "index.html"
        check(target.exists(), f"{label} link {href} resolves")

# ------------------------------- 5. no external requests, no tracking, no JS
print("\nNo third-party requests or tracking")
external = set()
for name, source in pages.items():
    for attribute in re.findall(r'(?:src|href)="(https?://[^"]+)"', source):
        external.add(f"{name}: {attribute}")
check(not external, f"no external src/href {sorted(external) if external else ''}")

for name, source in pages.items():
    label = f"/{name}/" if name != "(root)" else "/"
    check("<script" not in source.lower(), f"{label} contains no script tag")
    check("googletagmanager" not in source and "google-analytics" not in source, f"{label} has no analytics")
    check("@import" not in source and "fonts.googleapis" not in source, f"{label} loads no third-party font")

css = (ROOT / "assets" / "style.css").read_text(encoding="utf-8")
check("@import" not in css, "stylesheet imports nothing external")
check("url(http" not in css, "stylesheet fetches no remote asset")

# --------------------------------------------- 6. placeholders are visible
print("\nUnresolved placeholders are shown, not hidden")
placeholder_pattern = re.compile(r"\[([A-Z][^\]<>]*)\]")
found: dict[str, set[str]] = {}
for name, source in pages.items():
    for match in placeholder_pattern.finditer(source):
        found.setdefault(match.group(1), set()).add(name)

check(bool(found), "placeholders are present in the rendered output")
for name, source in pages.items():
    label = f"/{name}/" if name != "(root)" else "/"
    raw = placeholder_pattern.findall(source)
    marked = placeholder_pattern.findall(
        "".join(re.findall(r'<span class="placeholder">([^<]*)</span>', source))
    )
    check(
        len(raw) == len(marked),
        f"{label} every placeholder is marked up ({len(marked)}/{len(raw)})",
    )
    check("display:none" not in source.replace(" ", ""), f"{label} hides nothing with display:none")

# ---------------------------------------------- 7. source and output match
print("\nSource and published text agree")
spot_checks = [
    ("privacy", "No alert is sent to any person"),
    ("privacy", "Hera does not offer a wellbeing questionnaire"),
    ("terms", "Hera is not an emergency service."),
    ("terms", "Anonymity is limited to what other members see."),
    ("community-guidelines", "None of that breaks these rules."),
    ("mentor-agreement", "You are not a crisis service"),
]
for route, phrase in spot_checks:
    check(phrase in pages[route], f"/{route}/ contains: {phrase[:44]}...")

# ---------------------------------------------------- 8. must NOT be public
print("\nInternal artifacts are absent")
forbidden_files = ["CHANGE_LOG.md", "RETAINED_PROVISIONS.md", "IMPLEMENTATION_PLAN.md",
                   "APP_STORE_PRIVACY_MATRIX.md", "APP_REVIEW_CHECKLIST.md",
                   "OPEN_LEGAL_CLINICAL_ISSUES.md", "ROLLBACK_PLAN.md"]
present = [f for f in forbidden_files if list(ROOT.rglob(f))]
check(not present, f"no internal analysis documents {present if present else ''}")
check(not list(ROOT.rglob("*.sql")), "no migrations")
check(not list(ROOT.rglob(".env*")), "no environment files")
check(not list(ROOT.rglob("*.tsx")), "no application source")

print()
if failures:
    print(f"{len(failures)} CHECK(S) FAILED")
    for failure in failures:
        print(f"  - {failure}")
    sys.exit(1)

print("All checks passed.")
print(f"\nDistinct unresolved placeholders ({len(found)}):")
for text in sorted(found):
    where = ", ".join(sorted(found[text]))
    print(f"  [{text}]  ->  {where}")
