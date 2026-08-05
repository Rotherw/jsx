# WorkShop3D Auto Publisher

Local automation that prepares, publishes and promotes **finished** 3D-model
products for the **WorkShop3D** brand. It watches a folder, and when you drop a
finished product into it, it builds the sales listing, graphics and package,
publishes to the enabled stores, posts to the enabled social channels, records
the links, and writes a final report — all without touching your original
files.

> **Boundary (important).** This system is **not** a model generator. It never
> creates, repairs, rescales, cuts, re-meshes, adds supports to, or otherwise
> modifies STL / GLB / 3MF geometry. Automation begins **only** once finished
> files are placed in the *"Gotowe do sklepu"* folder. Delivered files are
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

1. Download this folder to your PC (green **Code → Download ZIP** on GitHub,
   then unzip; the program is the `workshop3d_publisher` folder).
2. Double-click **`install.bat`** — it installs Python if needed (via winget),
   sets everything up, makes a **desktop shortcut**, and launches the app. From
   then on just use the **"WorkShop3D Publisher"** shortcut on your desktop.
3. The dashboard opens in your browser. Click **⚙ Ustawienia** and fill the
   simple form: your folders, which stores to enable, and paste your API
   keys. Click **Zapisz** — that's it. **You never edit a config file or any
   code.**
4. (Optional) Double-click **`autostart_setup.bat`** to launch it automatically
   with Windows.

The **first run is DRY_RUN** by default: it prepares everything but publishes
nothing externally. Flip to real publishing from the Settings page (untick
*Tryb testowy*, tick *Publikuj automatycznie*).

> Everything below (config keys, YAML) is reference for power users. As a
> normal user you only ever touch the **Settings** page in the dashboard.

### Daily use

Just create a folder inside *"Gotowe do sklepu"* and drop the files in:

```
Gotowe do sklepu/
└── Dark Fantasy Dungeon Door/
    ├── Dark Fantasy Dungeon Door.png     (required: >= 1 PNG)
    ├── Dark Fantasy Dungeon Door.stl     (required: >= 1 STL)
    ├── Dark Fantasy Dungeon Door.glb     (optional)
    └── Dark Fantasy Dungeon Door.3mf     (optional)
```

No JSON/YAML/README from you is required — a PNG and an STL are enough. The
folder name is the working product name. Extra PNGs/STLs are all treated as part
of the product; GLB/3MF are extra formats.

The dashboard shows every detected product, its state in plain language, the
working links, error messages, and buttons to **retry**, **open the folder**,
and **stop/resume** automation.

---

## Modes (edit `config/config.yaml`, no code changes)

```yaml
modes:
  dry_run: true       # prepares everything, publishes nothing (default)
  auto_publish: false # set true (and dry_run false) to publish for real
```

- **DRY_RUN** — detect → validate → fact card → descriptions → graphics →
  package → *simulated* publish. Safe to run anytime.
- **AUTO_PUBLISH** — full run: publishes to enabled + connected platforms,
  saves real links, posts to social.

---

## Product lifecycle (states)

`DETECTED → WAITING_FOR_REQUIRED_FILES → VALIDATING → PREPARING_PRODUCT →
PREPARING_MEDIA → READY_TO_PUBLISH → PUBLISHING → PUBLISHED → PROMOTING →
COMPLETED` — plus `COMPLETED_WITH_WARNINGS`, `NEEDS_ATTENTION`, `FAILED`.

State is persisted to `work/state.json` after every transition, so a restart of
the program or the computer never loses progress. Processing is **idempotent** —
re-running never creates duplicate listings or posts, and adding a GLB/3MF later
**updates** the existing product instead of creating a second one.

---

## What it generates (per product)

- Sales title / short title / ASCII slug / ZIP name (originals never renamed).
- English store description + Polish description, with the signature
  *"Regards. / Rafal z WorkShop3D"*.
- Included-files list, **only confirmed** print information (no invented scale,
  material, print time, supports, game compatibility or lore).
- Exactly 20 tags where the platform allows (15 product + 5 brand/series).
- Category, price (from configurable rules), and per-platform licence summary.
- Product graphics from your PNG (cover, Thangs thumbnail, Cults3D, vertical +
  square social) — geometry never altered; only formats that actually exist are
  shown.
- A working copy + sales ZIP under `work/products/<id>/` (README + LICENSE
  included). **Your originals in "Gotowe do sklepu" are never modified.**
- `publication_report.json` and `publication_report.md`, plus a Windows toast.

---

## Secrets — never in the repo

No passwords, tokens or API keys are stored in code or config. Adapters read
them from **environment variables** only, and they are never printed to logs.
Set them in Windows (System → Environment Variables) or a local `.env`
(git-ignored):

| Platform          | Environment variables                          |
|-------------------|------------------------------------------------|
| Cults3D           | `CULTS3D_API_USER`, `CULTS3D_API_KEY`          |
| Google Drive host | `GOOGLE_APPLICATION_CREDENTIALS` (service-account JSON path) |
| Thangs            | `THANGS_API_TOKEN`                             |
| Creality Cloud EU | `CREALITY_EU_BROWSER_PROFILE` (browser session)|
| Creality Cloud CN | `CREALITY_CN_BROWSER_PROFILE` (browser session)|
| Facebook          | `FB_PAGE_ID`, `FB_PAGE_TOKEN`                  |
| Instagram         | `IG_USER_ID`, `IG_ACCESS_TOKEN`                |
| TikTok            | `TIKTOK_ACCESS_TOKEN`                          |
| YouTube           | `YOUTUBE_ACCESS_TOKEN`                          |

---

## Honest status of the publishing adapters

This MVP is **fully working end-to-end in DRY_RUN** and has a complete,
decoupled adapter architecture. Live publishing is wired **honestly**:

- **DRY_RUN** → every adapter simulates and returns a preview link; nothing is
  sent anywhere.
- **No credentials** → the adapter reports `NOT_CONNECTED` (it never fakes a
  successful publish).
- **Credentials present** →
  - **Cults3D** is **fully wired** to the real GraphQL API (`createCreation`) —
    see *Connecting Cults3D* below.
  - **Thangs** is **wired via the official Thangs Sync client** — the adapter
    stages files + metadata and reports `STAGED`; you press Start Upload in
    Thangs Sync to finish. See *Connecting Thangs* below.
  - **Creality Cloud (EU/CN)** is **wired via the official Batch Upload Tool** —
    the adapter stages files + a metadata sheet and reports `STAGED`; you upload
    from the tool. See *Connecting Creality Cloud* below.
  - The social adapters attempt their real call at a clearly marked connection
    point and, until wired to a **verified** account, raise clearly rather than
    pretend — so a report never claims a publish that did not happen.

## Connecting Cults3D (live)

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

The program uploads the product's images + package **ZIP** into a `FolderSync`
folder on your Google Drive, marks them public, and builds Cults-compatible
direct links automatically. One-time setup:

1. In Google Cloud Console: create a project → enable the **Google Drive API**
   → create a **service account** → create a **JSON key** and download it.
2. On Google Drive, create the folder **`FolderSync`** and **share it** (Editor)
   with the service account's e-mail (looks like
   `name@project.iam.gserviceaccount.com`).
3. Set the environment variable `GOOGLE_APPLICATION_CREDENTIALS` to the path of
   that JSON key file.
4. In config, keep `asset_hosts.google_drive.root_folder_name: "FolderSync"`.

The program then creates `FolderSync/<product_id>/`, uploads there, and links
Cults3D to those files. Re-runs reuse the same files (no duplicates). Because
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

## Connecting Thangs (live)

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

## Connecting Creality Cloud (live)

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

Browser-automation adapters (Creality) are designed to reuse an existing
logged-in session and will **never** bypass CAPTCHA or 2FA, never store
passwords, and stop that one adapter and ask you to act if they hit a block. A
failure on one platform never stops the others.

---

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
