# hera-legal

The public legal pages for **Hera**, an unincorporated, student-led peer-support project in Singapore.

> **Status:** the pages at the published URL are the documents in force. The `source/` text may be
> ahead of them between a revision and its publication; the version line at the top of each document
> says which version a page is.

## Pages

This repository is named `legal` and owned by the `heraformothers` organisation, so GitHub Pages
publishes it at **`https://heraformothers.github.io/legal/`**. That base path *is* the `/legal/`
route, which is why the repository root holds the index rather than a `legal/` folder.

| Published URL | Page |
|---|---|
| `/legal/` | Index of all documents |
| `/legal/privacy/` | Privacy Notice |
| `/legal/terms/` | Terms of Use |
| `/legal/community-guidelines/` | Community Guidelines |
| `/legal/mentor-agreement/` | Mentor Agreement |
| `/legal/support/` | Contact details and crisis resources |
| `/legal/peer-support/` | Peer Support & Mentorship Safety (written in `scripts/build.py`; its version is `PEER_SUPPORT_VERSION`) |

Two compatibility routes exist so that links already stored in the app never 404:

| Published URL | Forwards to | Why |
|---|---|---|
| `/legal/mentor-code/` | `/legal/mentor-agreement/` | `legal_documents.mentor_code.url` uses the old name |
| `/legal/legal/` | `/legal/` | Guards against a doubled path |

Keep both. Deleting a forwarding page breaks a link a mother may tap from inside the app.

## These URLs are permanent

**Never change a route to publish a new version.** The app stores these URLs in its `legal_documents` table and links to them from the sign-up consent screen and from Settings; a mother who accepted version A must still be able to open the page at the same address.

To publish a revision, edit the Markdown in `source/` and rebuild. The URL stays the same and the version inside the page changes.

If a route ever genuinely has to move, leave a forwarding page at the old address. Do not delete it.

## Updating a document

```bash
# 1. edit the Markdown
$EDITOR source/PRIVACY_NOTICE.md

# 2. bump the version line at the top of that file, e.g. 2026-08-05.1 -> 2026-09-01.1

# 3. rebuild and verify
python3 scripts/build.py
python3 scripts/verify.py

# 4. commit and push; GitHub Pages redeploys automatically
```

`source/` is the editable source of truth. The generated HTML is committed too, so the published site is always inspectable in the repository.

### Keeping the app in step

A material change means bumping the version in **three** places, or the app's consent gates will disagree with the pages:

1. the version line in the Markdown source here;
2. `legal_documents.current_version` in Supabase (a migration, needs separate approval);
3. the bundled fallback in the app's `src/constants/legal.ts`.

Bumping the server version forces every user to re-read and re-acknowledge. That is intended for a material change — do not do it for a typo fix.

## Before this site goes live

- [ ] Replace every review placeholder — run `python3 scripts/verify.py`, which lists them
- [ ] Set the effective date on all four documents
- [ ] Remove the draft banner (`DRAFT_BANNER` in `scripts/build.py`)
- [ ] Remove `<meta name="robots" content="noindex, nofollow">` (in the `page()` template)
- [ ] Confirm every route returns HTTP 200 on a physical phone
- [ ] Point `EXPO_PUBLIC_LEGAL_BASE_URL` and `legal_documents.url` at the final base URL

## Design constraints

Please keep these:

- **No JavaScript, no analytics, no cookies, no tracking pixels, no third-party fonts.** People read these pages precisely to find out what Hera does with their data; the pages themselves must collect nothing.
- **Semantic HTML.** Real headings, real tables, selectable text — never images of text.
- **Tables stack into labelled cards below 40rem** rather than shrinking, so the data inventory stays readable on a phone.
- **Black and white**, system fonts, generous line height.

`scripts/build.py` is a small dependency-free Markdown converter. It handles only the subset these documents use. If a document needs a construct it does not support, extend the converter rather than hand-editing the generated HTML — hand edits are overwritten on the next build.

## What is deliberately not here

No application source, no database migrations or schema, no environment files, no Supabase keys, no internal audits, decision memos or implementation plans, no test data, no user data. This repository contains the published documents and nothing else.

## Contact

heraformothers@gmail.com
