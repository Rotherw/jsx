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

## Quick start (Windows, no terminal needed)

1. Install **Python 3.11+** from python.org (tick *"Add Python to PATH"*).
2. Double-click **`install.bat`** — creates a local environment, installs
   dependencies, and copies `config/config.example.yaml` to
   `config/config.yaml`.
3. Open `config/config.yaml` and set your folders (see below).
4. Double-click **`run.bat`** — starts the watcher and opens the dashboard at
   <http://127.0.0.1:5000/>.
5. (Optional) Double-click **`autostart_setup.bat`** to launch it automatically
   with Windows.

The **first run is DRY_RUN** by default: it prepares everything but publishes
nothing externally.

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
- **Credentials present** → the adapter attempts the real call. The final HTTP
  wiring for each platform (Cults3D GraphQL upload, Thangs upload, the Graph/
  Data APIs, and the Creality browser flow) is the marked connection point in
  each adapter file. Until it is wired to a **verified** account it raises
  clearly rather than pretend — so a report never claims a publish that did not
  happen.

Browser-automation adapters (Creality) are designed to reuse an existing
logged-in session and will **never** bypass CAPTCHA or 2FA, never store
passwords, and stop that one adapter and ask you to act if they hit a block. A
failure on one platform never stops the others.

---

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
