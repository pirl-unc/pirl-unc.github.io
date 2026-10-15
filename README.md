# PIRL website

The Personalized Immunotherapy Research Lab website: a small Python/Jinja static
site intended for **GitHub Pages**. Most lab updates require editing YAML, not
HTML or Python. Images and fonts are included in the repository; Adobe Garamond
currently uses an external Adobe Fonts loader.

- **Repository after renaming:** `pirl-unc/pirl-unc.github.io`
- **Initial GitHub Pages address:** https://pirl-unc.github.io/
- **Final domain:** https://pirl.unc.edu
- **Migration status:** first GitHub deployment and domain cutover are pending. The separate hosted prototype is not GitHub Pages.

## Quick guide for lab members

### Make a change in GitHub without installing anything

1. Open the relevant file using the table below and click the pencil (Edit).
2. Make your change. Keep the existing indentation; YAML uses spaces, not tabs.
3. Choose **Create a new branch for this commit and start a pull request**.
   Give it a short description, such as “Add Jane to the People page”.
4. For photos, upload the image into the appropriate `static/assets/` folder on
   that same branch, then edit the YAML to reference it. Filename case matters.
5. Ask another lab member to review the pull request. The **Check site** workflow
   validates the source and builds it without publishing. It does not create a
   public preview URL or inspect the visual appearance.
6. Merge into `main` when ready. **Build and deploy** publishes the update.
   Watch the Actions tab; a change is live only after deployment succeeds.

You need repository write access to create branches directly. Otherwise, use a
fork and pull request or ask a repository administrator for access. Direct edits
to `main` also deploy, so use pull requests for ordinary changes.

### Which file should I edit?

| Change | File | Images |
| --- | --- | --- |
| Add a person, change a role, move someone to alumni | `data/people.yml` | `static/assets/people/` |
| Add or update a publication | `data/papers.yml` | `static/assets/papers/` |
| Feature software or hide a repository from the list | `data/tools.yml` | `static/assets/code/` |
| Update addresses, contact emails, investigator portraits | `data/contact.yml` | `static/assets/contact/` |
| Change navigation, blog URL, number of recent posts, social links | `data/site.yml` | Logo paths are in this file |
| Change the homepage introduction | `templates/index.html` | — |
| Change footer logo or Adobe Fonts loader | `data/appearance.yml` | `static/assets/` |
| Change colors, spacing, columns, typography | `static/site.css`, `static/fonts.css` | — |
| Change the shared header or footer | `templates/base.html` | — |

Do not edit `_site/` or `dist/`: these are generated and replaced by each build.
`data/posts.json` and `data/repos.json` are automatic caches, not the normal
editing interface. Publish blog articles on Substack.

### Add a person

Upload `jane-doe.jpg` to `static/assets/people/`, then add an entry under the
appropriate group's `people:` list in `data/people.yml`, matching its indentation:

```yaml
- name: Jane Doe
  role: Research Scientist
  photo: jane-doe.jpg
  links:
    - Website: https://example.org/
    - Scholar: https://scholar.google.com/
    - GitHub: https://github.com/example
```

Replace the example links with the person's own profiles, or omit `links`.
To add a personal research website later, add `- Website: https://example.org/`
under that person’s `links:` list. Use the `Website` label consistently; it appears
alongside Scholar, ORCID, and other profile links. Only add verified personal
research sites, and omit the entry when no site is known.

`role` is optional. Use a portrait with room around the face: photos are cropped
to 3:4. Keep filenames simple, such as `jane-doe.jpg`.

To move someone to alumni, move their complete entry into the Alumni group.
Group `layout` values are `investigators`, `members` (default), and `alumni`;
layout follows the group rather than its position in the file.

### Add a publication

Add to the top of `papers:` in `data/papers.yml`. This example shows the schema;
replace all example content and supply the image file before merging:

```yaml
- title: "Example paper title: a descriptive subtitle"
  authors: Jane Doe, John Doe
  venue: Example Journal
  year: 2026
  url: https://example.org/paper
  images:
    - assets/papers/example-paper.png
  paragraphs:
    - A short summary of the question and principal result.
    - An optional second paragraph describing its relevance.
```

Entries without figures use a separated, full-width text layout.

Put the figure at `static/assets/papers/example-paper.png`. For no figure use
`images: []`. The template displays title, authors, figures, and paragraphs;
`venue` and `year` are metadata and are not currently displayed. Verify the
publication link before merging. Use `paragraphs` as the single description
source; do not add a duplicate `summary` field.

### Feature a software tool

Add under `featured:` in `data/tools.yml`:

```yaml
- name: Example Tool
  url: https://github.com/pirl-unc/example-tool
  image: assets/code/example-tool.png
  description: A short explanation of what the tool does and who it is for.
```

Upload the image to `static/assets/code/`. The separate repository table refreshes
from the `pirl-unc` GitHub organization. To exclude a repository from that table,
add its exact name to `hide_repos`, for example `hide_repos: [example-tool]`.
This does not remove a manually featured tool.

### Contacts and YAML pitfalls

`data/contact.yml` has ordinary `sections` and a separate `investigators` section.
Each investigator carries their own `image` path, so reordering contacts keeps
portraits attached to the correct names.

- Quote text containing `: ` or ` #`, e.g. `"Lineberger (LCCC) | CB # 7599"`.
  Otherwise YAML can interpret the text as structure or a comment.
- Use `>-` for a long paragraph wrapped across source lines. Follow the existing
  indentation. Use a list for separate paragraphs.
- Most content is plain text and HTML-escaped. `tools.yml`'s `intro` explicitly
  supports HTML; do not paste scripts or untrusted HTML into it.
- Store public website content only. The intended repository and website are public.

## Developer setup and local preview

Requirements: Python 3.12 and Git. No Node.js, database, or application server is
needed. Once the repository has been created:

```sh
git clone https://github.com/pirl-unc/pirl-unc.github.io.git pirl-website
cd pirl-website
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
SITE_URL=http://localhost:8000 python build.py
python -m http.server --directory _site 8000
```

Open http://localhost:8000. Re-run the build after editing; there is no automatic
reload. On Windows, activate with `.venv\Scripts\Activate.ps1` and set the URL
using `$env:SITE_URL = "http://localhost:8000"` before `python build.py`.

Tests are offline and replace `_site/`. They check feed/image parsing, cache
fallback, local links, root/project URLs, reordered content, and output-directory
safety. They do not test browser appearance or mobile-menu interactions.

`SITE_URL` determines navigation prefixes and canonical URLs. To check the
GitHub project path, build with `SITE_URL=https://pirl-unc.github.io/pirl-site`.
The deployment workflow obtains the actual address from GitHub Pages settings.
`OUTPUT_DIR` accepts only `_site` (default) or `dist`, both disposable directories.

### Source structure and new pages

- `build.py`: loads data, sets URL helpers, and renders pages.
- `templates/`: one Jinja template per page, extending `base.html`.
- `static/`: copied unchanged into the published site.
- `scripts/`: refreshes blog/repository caches and imports remote portrait assets.
- `tests/`: standard-library unittest tests.
- `.github/workflows/check.yml`: pull request checks; no publishing or feed writes.
- `.github/workflows/build.yml`: refresh, build, and publish from `main`.

To add a page, create a template extending `base.html`, add its template/output
path to `PAGES` in `build.py`, and add navigation in `data/site.yml`. Use
`site_path('/new-page/')` for internal links and `asset('assets/...')` for local
images so the page works both under `/pirl-site/` and at the final domain root.
Add a new YAML file to the loading/context section of `build.py` if needed.

## Blog posts and automatic updates

The deployment workflow runs on pushes to `main`, manual dispatch, and every six
hours (`23 */6 * * *`, UTC; scheduled runs can be delayed).

1. Run offline tests.
2. Fetch Substack RSS and public GitHub repositories.
3. Commit changed caches and downloaded covers.
4. Build HTML and publish through GitHub Pages.

Covers are extracted from image enclosures, Media RSS, or article HTML in the
feed and downloaded to `static/assets/posts/`. Posts without art show a short plain-text excerpt from the RSS article body (up to 60 words), falling back to the subtitle when unavailable. Cached excerpts survive feed failures. Posts remain text-only,
with spacing and thin dividers. No substitute logo is used.

If RSS fails, a valid existing post cache remains untouched; a first import with
no usable cache fails. Cover failures retain an older downloaded cover when
available. A successful deployment can therefore still contain older posts:
check the refresh step's warnings if an article is missing. Repository-refresh
failures likewise keep the existing repository cache.

To refresh manually, open Actions → Build and deploy → Run workflow (`main`).
For local maintenance:

```sh
python scripts/fetch_posts.py
python scripts/fetch_posts.py --cached-only  # download known covers without RSS
python scripts/fetch_repos.py
```

Public-repository schedules can be disabled after 60 days without repository
activity. Check Actions if updates stop, then re-enable the workflow if needed.

## Deployment setup (repository administrators)

1. Create the public repository `pirl-unc/pirl-unc.github.io`, with `main` as its default
   branch, and push this source tree, including `.github/workflows/` and assets.
2. In Settings → Pages, set **Source: GitHub Actions**.
3. Ensure repository/organization Actions policy permits these workflows and
   the built-in token's requested permissions. Deployment needs `pages: write`
   and `id-token: write`; cache commits need `contents: write`.
4. Run **Build and deploy** from Actions. Wait for both build and deploy to
   succeed, then inspect https://pirl-unc.github.io/ on desktop and phone.
5. If branch protection prevents bot cache commits, adjust the update workflow
   to use a reviewed PR or separate cache storage; do not disable review rules
   merely to make the bot push. Failed cache pushes currently fail the workflow.

No personal access token is required for scheduled builds: they use GitHub's
built-in `GITHUB_TOKEN`. Pull requests run read-only checks and cannot publish.
The workflows do not configure branch-protection settings automatically.

## Moving pirl.unc.edu from Squarespace

**Do this after the GitHub Pages address works.** Keep Squarespace running during
the transition and until rollback is no longer needed.

DNS checked on 2026-10-15:

| Name | Type | Existing target | New target |
| --- | --- | --- | --- |
| `pirl.unc.edu` | CNAME | `ext-cust.squarespace.com` | `pirl-unc.github.io` |

The observed DNS TTL was 3600 seconds. Recheck before cutover; the DNS
administrator may be able to lower it in advance.

1. In the **pirl-unc organization** Settings → Pages, add `pirl.unc.edu` as a
   verified domain. GitHub supplies an exact TXT name/value. Ask the existing
   UNC DNS administrator to publish it, then verify it in GitHub. Keep that TXT
   record. This is separate from the repository's custom-domain setting.
2. In the repository Settings → Pages, save **Custom domain: `pirl.unc.edu`**
   before switching the CNAME. This may redirect the default GitHub Pages URL,
   so do it as part of the planned cutover after reviewing that URL.
3. Re-run Build and deploy after setting the custom domain, so generated asset
   paths use the domain root instead of `/pirl-site/`.
4. Ask the UNC team managing this hostname to replace its current CNAME with
   `pirl-unc.github.io`. Do not include `https://`, `/pirl-site/`, or a trailing
   URL path. Do not change the nameservers or records for the rest of `unc.edu`.
5. Wait for GitHub's DNS check and certificate provisioning; enable **Enforce
   HTTPS** when available. DNS propagation and certificate issuance can take
   time. Check the final HTTPS URL, all navigation, images, and `/research/`.
6. Keep the old site available until the new site has been checked on desktop
   and mobile, and fonts and feed updates work independently of Squarespace.

GitHub Actions publishing does not require a source-tree `CNAME` file; configure
the custom domain in Pages settings. Domain control is separate from GitHub
repository access: UNC's DNS administrator must make the DNS change.

Suggested text for the UNC DNS request (send only when the GitHub site is ready):

> Please coordinate moving pirl.unc.edu from Squarespace to GitHub Pages for
> the Personalized Immunotherapy Research Lab. Replace its CNAME target
> ext-cust.squarespace.com with pirl-unc.github.io. Please preserve unrelated
> UNC DNS records. We will first provide GitHub's domain-verification TXT
> record for publication and verify it, configure the repository's custom
> domain, and agree on a cutover time. The current observed TTL is 3600 seconds;
> can it be reduced in advance? Please retain the old target for rollback.

We have not confirmed the internal UNC owner of this DNS record. Start with the
team that configured the Squarespace mapping or your departmental IT contact.

### Rollback and troubleshooting

| Symptom | What to check |
| --- | --- |
| YAML/build failure | Open the failed Actions step; check indentation, quotes, and required fields. The previous deployment remains live if a new deployment fails. |
| Change not visible | Verify the edit merged into `main`, deployment succeeded, and the browser is not showing a cached copy. |
| Broken photo | Check exact filename/case, folder, and YAML path. Uploaded files must be on the same branch. |
| New post missing | Inspect RSS refresh warnings; cached posts may be served during an outage. |
| Pages 404 | Check Pages source, successful deploy job, repository path, and custom-domain setting. |
| Styles missing after cutover | Re-run deployment with the custom domain saved; confirm generated links no longer start with `/pirl-site/`. |
| Certificate pending | Check the CNAME and GitHub Pages DNS status; allow provisioning time. |

For a content mistake, revert the merged pull request in GitHub (or use
`git revert <commit>` on a new branch), review, and merge. This creates a new
commit and redeploys without rewriting history.

For a failed domain cutover, ask the DNS administrator to restore the previous
CNAME `ext-cust.squarespace.com` while Squarespace remains active. DNS caches can
retain the new record until its TTL expires. To restore the GitHub project URL
as well, remove the custom domain in Pages settings and rerun deployment.

## Remaining migration checks

- Verify a successful live RSS fetch in GitHub Actions; the original preview
  environment returned an HTML “Site Unavailable” page, so its cache was seeded.
- Review desktop/mobile layout, keyboard navigation, and contact details.
- Confirm Adobe Garamond's external font loader works on the final domain or
  replace it with an appropriately licensed font. Other bundled fonts are local.
- Verify imported publication URLs and image permissions before cutover.
- The old contact form is not migrated; the Contact page lists email addresses.

References:

- [GitHub: custom domain configuration](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)
- [GitHub: verifying an organization domain](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages)
- [GitHub: HTTPS](https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https)

Software images are optional: omit `image` for a text-only entry. Do not substitute
the lab logo for missing artwork. Featured software is curated in `data/tools.yml`;
the automatic public repository table is separate.
