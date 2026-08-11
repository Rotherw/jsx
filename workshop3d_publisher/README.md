# WorkShop3D Auto Publisher

Local automation that prepares, publishes and promotes **finished** 3D-model
products for the **WorkShop3D** brand. It watches **Google Drive → Folder Sync →
Gotowe do sklepu**, and when you drop a finished product folder into it, it
builds the sales listing, graphics and package,
publishes to the enabled stores, posts to the enabled social channels, records
the links, and writes a final report — all without touching your original
files.

> **Boundary (important).** This system is **not** a model generator. It never
> creates, repairs, rescales, cuts, re-meshes, adds supports to, or otherwise
> modifies STL / GLB / 3MF geometry. Automation begins **only** once finished
> files are placed in *FolderSync/Gotowe do sklepu*. Delivered files are
> treated as final.

---

## Why Python?

- First-class on Windows and easy to package into a single `.exe` later
  (PyInstaller).
- Mature libraries for every part of this job: `watchdog` (folder monitoring),
  `Pillow` (PNG validation + product graphics), `Flask` (local dashboard),
  `plyer` (Windows toast notifications), `pytest` (tests).
- Clear module separation, so adding a new store or social platform is one
  small file — no rebuild of the core.

---

## Quick start (Windows — no code, no config files)

1. Download the ZIP and extract it.
2. Double-click the top-level **`1_ZAINSTALUJ.bat`** — it updates an existing
   installation in place or installs a new one. It installs Python and, when missing,
   Google Drive for desktop, sets everything up, makes a desktop shortcut,
   enables hidden Windows autostart and launches the app. In the background it
   opens the official Nextcloud authorization and the paired Chrome extension
   accepts it automatically when that Chrome profile is already signed in. The
   app receives a separate revocable app password, never your account password
   or Chrome cookies, and does not download the whole Nextcloud onto the PC. All
   Publisher pages are opened explicitly in Google Chrome, using the profile
   where you are already logged in, even when Windows has another default browser.
3. The installer writes the private local Chrome connection itself; there is no
   code to copy and no Settings form to complete. If Chrome has not loaded the
   Publisher extension before, the installer opens `chrome://extensions` and
   the exact extension folder. Chrome requires one local **Load unpacked**
   confirmation; after that it reuses the tabs and login sessions already
   present in normal Chrome. The app never copies passwords or cookies.
4. If Google Drive asks for sign-in, do it once. Koniec konfiguracji. The
   publisher starts invisibly with Windows. From then on, only drop a
   product folder into **Google Drive → Folder Sync → Gotowe do sklepu**.

Nowa instalacja uruchamia **pełny automat**. Codzienna praca polega wyłącznie na
wrzuceniu folderu produktu. Tryb testowy i ręczne zatwierdzanie pozostają
dostępne pod ukrytym adresem ustawień zaawansowanych.

> Everything below (config keys, YAML) is reference for power users. Normal
> daily use does not require opening Settings.

### Daily use

Drop one complete folder into the Google cloud inbox:

```
Folder Sync/
├── Gotowe do sklepu/
│   └── Dark Fantasy Dungeon Door/
│       ├── Dark Fantasy Dungeon Door.png     (required: >= 1 PNG)
│       ├── Dark Fantasy Dungeon Door.stl     (required: >= 1 STL)
│       ├── Dark Fantasy Dungeon Door.glb     (optional)
│       └── Dark Fantasy Dungeon Door.3mf     (optional)
└── Opublikowane/                            (managed automatically)
```

No JSON/YAML/README from you is required — a PNG and an STL are enough. The
folder name is the working product name. Extra PNGs/STLs are all treated as part
of the product; GLB/3MF are extra formats.

The dashboard shows every detected product, its state in plain language, the
live stage/percentage, completed-store count, exact finish time, working links
and any error that needs attention. It refreshes itself every five seconds.
Windows also shows a **GOTOWE** notification when the whole run has ended and
the product can be checked in the stores. At that point the same folder has
already been moved on Google and Nextcloud from `Gotowe do sklepu` to the
sibling `Opublikowane` folder.

### Google ↔ Nextcloud folder flow

- Google `Folder Sync/Gotowe do sklepu` is the main publishing inbox.
- Nextcloud uses `Folder Sync/Gotowe do sklepu` on `cloud.workshop3d.pl`.
- Nextcloud is accessed directly through its official Login Flow v2 + WebDAV;
  no second local copy of the whole cloud is required.
- The first run copies every existing product folder from Google into an empty
  Nextcloud inbox; later changes are checked automatically every 15 seconds.
- New and changed finished folders flow both ways. Complete product folders
  already present during installation are also added to the publishing queue.
- The same names and nested structure are preserved; no product-id copy and no
  `sync_manifest.json` are added.
- If the same file changed on both clouds, the newer version wins. Ordinary
  deletions are not propagated, so the surviving cloud restores the file.
- After the full store + cloud run, the folder is moved on both clouds to the
  sibling `Opublikowane` folder. Only then is the run marked **GOTOWE**.
- The app runs hidden at Windows sign-in. The desktop shortcut normally just
  opens the already-running dashboard; it does not start a second publisher.

---

## Modes (edit `config/config.yaml`, no code changes)

```yaml
modes:
  zero_touch: true    # drop the folder; preparation + upload + submit happen automatically
  dry_run: false
  auto_publish: true
  require_approval: false
```

- **DRY_RUN** — detect → validate → fact card → descriptions → graphics →
  package → *simulated* publish. Safe to run anytime.
- **AUTO_PUBLISH off** — prepares the complete preview and waits for your
  explicit **Zatwierdź i publikuj** click.
- **AUTO_PUBLISH on** — advances automatically, while the independent
  `require_approval` switch can still require a human preview. In browser mode
  Chrome fills, uploads and submits the forms. A manual final click remains
  available only as an advanced alternative.

---

## Product lifecycle (states)

`DETECTED → WAITING_FOR_REQUIRED_FILES → VALIDATING → PREPARING_PRODUCT →
PREPARING_MEDIA → SYNCING_CLOUDS → READY_TO_PUBLISH → AWAITING_APPROVAL →
PUBLISHING → AWAITING_BROWSER_REVIEW → PUBLISHED → PROMOTING → COMPLETED` — plus
`AWAITING_CLOUD_SYNC`,
`COMPLETED_WITH_WARNINGS`, `NEEDS_ATTENTION`, `FAILED`.

State is persisted to `work/state.json` after every transition, so a restart of
the program or the computer never loses progress. Processing is **idempotent** —
re-running never creates a second queued browser form or duplicate social post.
When product files change, the same local product record is rebuilt. A store
listing already marked `PUBLISHED` is not silently recreated; edit/update
support remains platform-specific.

---

## What it generates (per product)

- Sales title / short title / ASCII slug / ZIP name (originals never renamed).
- English store description + Polish description, with the signature
  *"Regards. / Rafal z WorkShop3D"*.
- Optional, confidence-gated lore enrichment from `wiki.kf2.pl`: exact/strong
  title matches are sourced and linked; ambiguous names are ignored.
- Included-files list, **only confirmed** print information (no invented scale,
  material, print time, supports, game compatibility or lore).
- Exactly 20 tags where the platform allows (15 product + 5 brand/series).
- Category, price (from configurable rules), and per-platform licence summary.
- Product graphics from your PNG (cover, Thangs thumbnail, Cults3D, vertical +
  square social) — geometry never altered; only formats that actually exist are
  shown.
- A working copy + sales ZIP under `work/products/<id>/` (README + LICENSE
  included). Product file contents are never modified; after success, the
  source folder itself is moved from `Gotowe do sklepu` to `Opublikowane`.
- `publication_report.json` and `publication_report.md`, plus a Windows toast.

---

## Secrets — never in the repo

No passwords, tokens or API keys are stored in code or config. Adapters read
them from **environment variables** only, and they are never printed to logs.
Set them in Windows (System → Environment Variables) or a local `.env`
(git-ignored):

| Platform / mode   | Environment variables                          |
|-------------------|------------------------------------------------|
| Paired Chrome     | none — installer prepares the local connection  |
| Cults3D API mode  | `CULTS3D_API_USER`, `CULTS3D_API_KEY`          |
| Google Drive host | `GOOGLE_APPLICATION_CREDENTIALS` (service-account JSON path) |
| Facebook          | `FB_PAGE_ID`, `FB_PAGE_TOKEN`                  |
| Instagram         | `IG_USER_ID`, `IG_ACCESS_TOKEN`                |
| TikTok            | `TIKTOK_ACCESS_TOKEN`                          |
| YouTube           | `YOUTUBE_ACCESS_TOKEN`                          |

---

## Honest status of the publishing adapters

The application is **fully working end-to-end in DRY_RUN** and uses an
authenticated local Chrome bridge for live store forms:

- **DRY_RUN** → every adapter simulates and returns a preview link; nothing is
  sent anywhere.
- **No credentials** → the adapter reports `NOT_CONNECTED` (it never fakes a
  successful publish).
- **Browser mode (recommended)** → Cults3D, Thangs and Creality Cloud EU/CN
  reuse an existing Chrome window, open/reuse the correct uploader tab, attach
  local model/images and fill discoverable title, description, tags, category,
  price and AI declaration fields. The extension never bypasses CAPTCHA/2FA.
  It reports `PUBLISHED` only after the browser reaches a recognised listing
  URL; merely filling or clicking a form is `READY_FOR_REVIEW`/`SUBMITTED`.
- **Fallback modes** → Cults3D still supports its GraphQL API; Thangs supports
  the official Sync staging flow; Creality EU/CN support the official Batch
  Upload Tool staging flow.
  - The social adapters attempt their real call at a clearly marked connection
    point and, until wired to a **verified** account, raise clearly rather than
    pretend — so a report never claims a publish that did not happen.

## Paired Chrome (recommended live mode)

The installer prepares the private local connection and opens the included
extension folder if Chrome still needs its one-time **Load unpacked** security
confirmation. No pairing code is copied or entered. Log into store and social
sites normally in Chrome once; those sessions stay owned by Chrome and the
publisher sees neither passwords nor cookies.

The Chrome confirmation happens once. Afterwards the default flow
uploads and submits automatically. Any extra question, CAPTCHA, policy checkbox
or changed form stops visibly in the store tab instead of being treated as
success.

## Connecting Cults3D API (optional alternative)

Cults3D is connected through its official **GraphQL API**
(`https://cults3d.com/graphql`, HTTP Basic auth).

**1. Get an API key** at <https://cults3d.com/en/api/keys> and set two
environment variables (never in config/code):

```
CULTS3D_API_USER = your Cults username
CULTS3D_API_KEY  = the generated key
```

**2. Host your files publicly (required by Cults3D).** Cults3D does **not**
accept file uploads — it references images and 3D files by **public HTTPS
URL** (max 10 each, and the URL must expose the filename + extension). Two
ways, chosen with `stores.cults3d.asset_host`:

**(a) Google Drive — recommended (`asset_host: "google_drive"`)**

The program uploads the product's images + package **ZIP** into a separate
`WorkShop3D Public Assets` folder, marks them public, and builds
Cults-compatible direct links automatically. This technical API-only folder is
kept out of the private `FolderSync` workflow. One-time setup:

1. In Google Cloud Console: create a project → enable the **Google Drive API**
   → create a **service account** → create a **JSON key** and download it.
2. On Google Drive, create **`WorkShop3D Public Assets`** and share it (Editor)
   with the service account's e-mail (looks like
   `name@project.iam.gserviceaccount.com`).
3. Set the environment variable `GOOGLE_APPLICATION_CREDENTIALS` to the path of
   that JSON key file.
4. Keep `asset_hosts.google_drive.root_folder_name: "WorkShop3D Public Assets"`.

The program creates `WorkShop3D Public Assets/<product_id>/`, uploads there,
and links Cults3D to those files. Re-runs reuse the same files (no duplicates). Because
it hosts the **ZIP** for the model (not raw STL) and PNGs for images, it stays
well within the 10-link limit and avoids Google's large-file download pages.

**(b) Your own web space (`asset_host: "static"`)**

If you mirror `work/products/` to your own public site, set
`asset_hosts.static.base_url` (or `stores.cults3d.asset_base_url`) and the
adapter builds `<base_url>/<product_id>/<filename>` links.

If URLs can't be produced (no credentials, folder not shared, no base URL), the
adapter **pauses that one listing** with `NEEDS_ATTENTION` and tells you exactly
what's missing — it never publishes a listing with broken links.

**3. Configure the listing** (all optional, in `stores.cults3d`):
`locale`, `license_code` (your Cults licence code), `category_id` (or let the
adapter match your product category to a Cults category by name),
`price_in_cents` (set `true` only if your account expects cents).

**4. Go live.** Set `modes.dry_run: false` and `modes.auto_publish: true`. On
publish the adapter runs `createCreation` and saves the returned creation **id
and URL**. New Cults creations land in your dashboard for a final check — the
adapter creates it and records the link; you confirm/finalise in Cults.

> **Price-unit note:** `downloadPrice` is sent as the amount from your pricing
> rules (e.g. `4.99`). If your Cults account expects cents, set
> `price_in_cents: true`. Because pricing is money, do a first live run on one
> product and verify the price in your Cults dashboard before batch-publishing.

Rate limits (~60 req/30 s, ~500/day) are handled with automatic exponential
backoff on `429`/`5xx`.

## Connecting Thangs Sync (optional fallback)

Thangs has **no public upload API**; its official automation path is the
**Thangs Sync** desktop client, which watches a folder and uploads each
subfolder as a model (metadata from a CSV). This adapter integrates with that
tool instead of faking an API.

**1. Install Thangs Sync** (from thangs.com), log in with your account, and
point it at a folder, e.g. `C:/Users/Rafal/WorkShop3D/ThangsSync`.

**2. Configure** `stores.thangs`:

```yaml
thangs:
  enabled: true
  mode: "sync"
  sync_folder: "C:/Users/Rafal/WorkShop3D/ThangsSync"
```

**3. Go live** (`modes.dry_run: false`). For each product the adapter:

- creates a subfolder in your Thangs Sync folder and copies the STL/3MF/GLB/PNG
  into it, and
- writes/updates `thangs_bulk_upload.csv` with the exact Thangs columns
  (`ModelName, Description, Tags, Category, SecondaryCategory`; tags separated
  by `:`).

Then you **open Thangs Sync and press Start Upload** — it uploads as you,
logged in. The adapter reports `STAGED` (not a fake "published") and the
product finishes as `COMPLETED_WITH_WARNINGS` with a reminder to run Sync,
because only Thangs Sync can confirm the final upload. Re-running never
duplicates the CSV row or the staged folder.

## Connecting Creality Batch Tool (optional fallback)

Creality Cloud has no public upload API either. Its official bulk path is the
**Model File Batch Upload Tool** (a desktop app that uploads models from a
folder, one subfolder per model). The EU and CN adapters integrate with it the
same "staging" way as Thangs.

**1. Download the Creality Cloud Batch Upload Tool** (crealitycloud.com →
Software), install it and log in.

**2. Configure** the region(s) you use:

```yaml
creality_cloud_eu:
  enabled: true
  mode: "batch"
  staging_folder: "C:/Users/Rafal/WorkShop3D/CrealityEU"
```

**3. Go live** (`modes.dry_run: false`). For each product the adapter creates a
subfolder in the staging folder, copies the model files + PNG into it, and
writes `creality_upload_info.txt` (title, category, tags, description, licence,
file list) for easy review. You then **open the Batch Upload Tool, point it at
the staging folder, review the metadata and upload**. Status is `STAGED` and
the product finishes `COMPLETED_WITH_WARNINGS` with a reminder — the adapter
never fakes a completed upload. A `mode: "browser"` alternative exists for
reusing a logged-in browser session (it stops and asks you on any CAPTCHA/login
block, and never stores passwords).

The paired extension is the primary browser mode for all four store targets.
A failure on one platform never stops the others.

---

## See everything before it is sent (approval gate)

With `modes.require_approval: true` (the default, toggleable in Settings), each
product is fully prepared and then **stops at `AWAITING_APPROVAL` — nothing is
sent yet**. Open the product in the dashboard to see a **preview**: the store
listing (title, description, tags, price, files), the generated graphics, and
the **exact text of every social post** (with the store tag and link). When it
looks right, click **"Zatwierdz i publikuj"** and only then does it publish and
promote. DRY_RUN also lets you preview freely without ever sending.

## Social media promotion (with automatic store tagging)

After at least one store listing succeeds, the enabled social adapters post a
promo with the product link **and automatically tag the store(s) the product
went live on** — `@cults3d`, `@thangs3d`, `@CrealityCloud` — which the
platforms say helps a post's reach. The handles are configurable
(`social.store_handles`) and de-duplicated (EU+CN → one `@CrealityCloud`).

Networks and their status:

All six adapters make the **real** API call. What differs is only how hard the
token is to obtain — and no code can bypass that, it's each platform's security
(a normal account is not enough; you create a developer app and paste the
token).

| Network | Real API call | Credentials (env / Settings page) |
|---|---|---|
| **Mastodon** | ✅ `POST /api/v1/statuses` | `MASTODON_INSTANCE_URL`, `MASTODON_ACCESS_TOKEN` |
| **Bluesky** | ✅ `createSession` → `createRecord` | `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD` |
| **Facebook** | ✅ `POST /{page}/feed` | `FB_PAGE_ID`, `FB_PAGE_TOKEN` |
| **Instagram** | ✅ `media` → `media_publish` (+ hosted image) | `IG_USER_ID`, `IG_ACCESS_TOKEN` |
| **X (Twitter)** | ✅ OAuth 1.0a `POST /2/tweets` | `X_API_KEY/SECRET`, `X_ACCESS_TOKEN/SECRET` |
| **Pinterest** | ✅ `POST /v5/pins` (+ hosted image) | `PINTEREST_ACCESS_TOKEN`, `PINTEREST_BOARD_ID` |

Enable networks and paste every credential from the dashboard **Settings**
page — no files to edit. DRY_RUN prepares each post without sending it; missing
credentials report `NOT_CONNECTED`; Instagram/Pinterest report `NEEDS_ATTENTION`
if no public image URL can be produced (they need the Google Drive asset host,
same as Cults3D). The X OAuth 1.0a signing is verified against X's own
documented example in the tests.

**Getting each token:**
- **Mastodon:** your instance → Preferences → Development → New application
  (scope `write:statuses`) → copy the access token.
- **Bluesky:** Settings → App Passwords → add one; use your handle + that
  password.
- **Facebook/Instagram:** create a Meta app at developers.facebook.com, connect
  your Page (and an IG Business/Creator account linked to it), and generate a
  Page access token with `pages_manage_posts` (+ `instagram_content_publish`
  for IG).
- **X:** create an app at developer.x.com, enable OAuth 1.0a with read+write,
  and copy the API key/secret + access token/secret.
- **Pinterest:** create an app at developers.pinterest.com, get an access token
  with the pins scope, and copy your target board id.

## Architecture (decoupled modules)

```
src/workshop3d/
  folder_watcher.py      detect + stability/debounce + ignore temp files
  file_validator.py      PNG/STL checks + checksums (read-only)
  product_analyzer.py    fact card: CONFIRMED / SAFE INFERENCES / UNKNOWN
  metadata_generator.py  titles, slug, descriptions, tags, category, price, licence
  brand_renderer.py      cover / thumbnails / social graphics from the PNG
  package_builder.py     work dirs, source+renamed copies, README, LICENSE, ZIP
  publication_manager.py runs store/social adapters (idempotent, isolated)
  pipeline.py            the state machine
  link_manager.py        central link card + main-link priority
  state_store.py         crash-safe JSON persistence
  notification_service.py Windows toast (stdout fallback)
  report.py              publication_report.json + .md
  dashboard/             local Flask status panel
  adapters/
    base.py              StoreAdapter / SocialAdapter + self-registration
    stores/              cults3d, thangs, creality_eu, creality_cn
    social/              facebook, instagram, tiktok, youtube
```

### Adding a new platform (e.g. MakerWorld, Printables)

Create one file under `adapters/stores/`, subclass `StoreAdapter`, decorate with
`@register_store`, set `key` to match a `stores.<key>` config block, and
implement `publish()`. Add it to `adapters/stores/__init__.py`. No core changes.

---

## Tests

```bash
pip install pytest
python -m pytest        # from the workshop3d_publisher/ directory
```

Covers: complete-folder detection, missing PNG, missing STL, extra GLB, extra
3MF, multiple STL, multiple PNG, copy-stability, duplicate protection, restart
resume, format-update without duplicate listing, per-platform failure
isolation, description generation without invented data, and DRY_RUN. **Tests
never perform real publications.**

---

## Command line (optional)

```bash
python -m workshop3d                 # watcher + dashboard (what run.bat does)
python -m workshop3d --scan-once     # process current folders once, then exit
python -m workshop3d --dashboard-only
python -m workshop3d --config path/to/config.yaml
```
