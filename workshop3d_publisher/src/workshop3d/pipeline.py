"""The product state machine (spec sections 4, 24).

Drives one product folder from DETECTED to a terminal state. Persists the
record after every transition so a restart resumes cleanly. Idempotent: it
never creates duplicate listings/posts and never modifies the originals.
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from .config import Config
from .file_validator import validate
from .models import PROGRESS_STEP_BY_STATE, PROGRESS_TOTAL, ProductRecord, State
from .state_store import StateStore
from . import (
    product_analyzer,
    metadata_generator,
    brand_renderer,
    package_builder,
    publication_manager,
    link_manager,
    report,
    notification_service,
    wiki_client,
    cloud_sync,
)


def product_id_for(folder_name: str, checksums: dict[str, str]) -> str:
    """Stable identity from folder name + file content hashes (dedup key)."""
    digest = hashlib.sha256()
    digest.update(folder_name.encode("utf-8"))
    for name in sorted(checksums):
        digest.update(name.encode("utf-8"))
        digest.update(checksums[name].encode("utf-8"))
    return digest.hexdigest()[:16]


class Pipeline:
    def __init__(self, config: Config, store: StateStore):
        self.config = config
        self.store = store

    # -- entry points -------------------------------------------------------
    def on_folder_ready(self, folder: Path) -> ProductRecord:
        """Called by the watcher once a folder looks stable/complete.

        Idempotent: an already-completed product whose files are unchanged is
        skipped. If a new format (GLB/3MF) was added, the SAME record is
        updated -- never a second listing (spec section 15).
        """
        record = self.store.find_by_folder(folder.name)
        if record is None:
            record = ProductRecord(
                product_id=f"pending-{folder.name}",
                folder_name=folder.name,
                folder_path=str(folder),
            )
            self._set(record, State.DETECTED)
            return self.run(record)

        # Existing product: has anything actually changed?
        current = validate(folder)
        stable_states = (
            State.COMPLETED.value,
            State.COMPLETED_WITH_WARNINGS.value,
            State.AWAITING_APPROVAL.value,
            State.AWAITING_BROWSER_REVIEW.value,
            State.AWAITING_CLOUD_SYNC.value,
        )
        if (
            self.config.zero_touch
            and record.state in (
                State.AWAITING_APPROVAL.value,
                State.READY_TO_PUBLISH.value,
            )
            and current.checksums == record.checksums
        ):
            # Migrate products left behind by an older/manual configuration.
            # The user selected zero-touch once at installation, so a stale
            # per-product approval must never keep an unchanged folder stuck.
            return self.publish_now(record)
        if record.state in stable_states and current.checksums == record.checksums:
            if cloud_sync.enabled(self.config) and (
                cloud_sync.should_retry(record.cloud_sync)
                or cloud_sync.should_retry(record.cloud_archive)
            ):
                return self.retry_cloud_sync(record)
            return record  # nothing new -> keep waiting/completed, no duplicate work
        # Files changed (e.g. GLB/3MF added) or not yet finished -> (re)process.
        record.folder_path = str(folder)
        return self.run(record)

    def run(self, record: ProductRecord) -> ProductRecord:
        """Advance a product as far as possible. Safe to call repeatedly.

        Idempotency across re-runs is guaranteed downstream: a store/social
        platform already PUBLISHED/POSTED is never published again.
        """
        folder = Path(record.folder_path)
        # A retry or a changed folder is a new run of the same product record.
        record.progress_step = 0
        record.progress_total = PROGRESS_TOTAL
        record.completed_at = None
        record.attempts += 1

        try:
            self._validate(record, folder)
            if record.state in (
                State.WAITING_FOR_REQUIRED_FILES.value,
                State.NEEDS_ATTENTION.value,
            ):
                return record

            self._prepare_product(record, folder)
            self._prepare_media(record)
            self._sync_clouds(record)
            self._set(record, State.READY_TO_PUBLISH)

            # DRY_RUN deliberately reaches the adapters because their dry-run
            # results are the useful preview.  In live mode, AUTO_PUBLISH=false
            # must genuinely prevent external writes.
            if not self.config.dry_run and not self.config.auto_publish:
                record.required_user_action = (
                    "Automatyczna publikacja jest wyłączona. Sprawdź podgląd i "
                    "kliknij 'Zatwierdź i publikuj'."
                )
                self._set(record, State.READY_TO_PUBLISH)
                return record

            # Human review gate: prepare everything, then stop before sending
            # anything externally until the user approves in the dashboard.
            require_approval = self.config.get("modes.require_approval", True)
            if not self.config.dry_run and require_approval:
                record.required_user_action = "Sprawdz podglad i kliknij 'Zatwierdz i publikuj'."
                self._set(record, State.AWAITING_APPROVAL)
                notification_service.notify(
                    "WorkShop3D: do zatwierdzenia",
                    f"{record.metadata.get('TITLE', record.folder_name)} czeka na Twoja akceptacje.",
                )
                return record

            self._publish(record)
            self._promote(record)
            self._finish(record)
        except Exception as exc:  # unexpected -> FAILED, but keep progress
            record.error_history.append(str(exc))
            self._set(record, State.FAILED)
            notification_service.notify("WorkShop3D: FAILED", f"{record.folder_name}: {exc}")
        return record

    def resume_zero_touch_pending(self) -> list[ProductRecord]:
        """Resume old prepared records at startup without asking for approval."""
        if not self.config.zero_touch:
            return []
        resumed: list[ProductRecord] = []
        for record in self.store.all():
            if record.state not in (
                State.AWAITING_APPROVAL.value,
                State.READY_TO_PUBLISH.value,
            ):
                continue
            record.required_user_action = None
            package_ready = bool(
                record.package_path and Path(record.package_path).is_dir()
            )
            folder_ready = Path(record.folder_path).is_dir()
            if package_ready:
                resumed.append(self.publish_now(record))
            elif folder_ready:
                resumed.append(self.run(record))
        return resumed

    def publish_now(self, record: ProductRecord) -> ProductRecord:
        """Run publish + promote + finish for an approved product (dashboard)."""
        record.required_user_action = None
        try:
            self._publish(record)
            self._promote(record)
            self._finish(record)
        except Exception as exc:
            record.error_history.append(str(exc))
            self._set(record, State.FAILED)
            notification_service.notify("WorkShop3D: FAILED", f"{record.folder_name}: {exc}")
        return record

    def resume_after_browser(self, record: ProductRecord) -> ProductRecord:
        """Recompute the product after Chrome reports a form/listing result."""
        browser_pending = any(
            item.get("status") in ("BROWSER_QUEUED", "READY_FOR_REVIEW", "SUBMITTED")
            for item in record.stores.values()
        ) or any(
            item.get("status") in ("BROWSER_QUEUED", "READY_FOR_REVIEW", "SUBMITTED")
            for item in record.social.values()
        )
        if publication_manager.has_live_listing(record):
            self._set(record, State.PUBLISHED)
            self._promote(record)
            self._finish(record)
        elif browser_pending:
            record.required_user_action = (
                "Sprawdź otwartą kartę Chrome i dokończ publikację w sklepie."
            )
            self._set(record, State.AWAITING_BROWSER_REVIEW)
        else:
            self._finish(record)
        return record

    def retry_cloud_sync(self, record: ProductRecord) -> ProductRecord:
        """Retry only both Folder Sync targets; never republish a store listing."""
        if not cloud_sync.enabled(self.config):
            return record
        if record.cloud_archive and not cloud_sync.archived(record.cloud_archive):
            record.cloud_archive = cloud_sync.archive_product(record, self.config)
        elif not cloud_sync.succeeded(record.cloud_sync):
            record.cloud_sync = cloud_sync.sync_product(record, self.config)
        self.store.upsert(record)
        if (
            cloud_sync.succeeded(record.cloud_sync)
            and record.state == State.AWAITING_CLOUD_SYNC.value
        ):
            self._finish(record)
        return record

    # -- stages -------------------------------------------------------------
    def _validate(self, record: ProductRecord, folder: Path) -> None:
        self._set(record, State.VALIDATING)
        result = validate(folder)
        record.png_files = result.png_files
        record.stl_files = result.stl_files
        record.glb_files = result.glb_files
        record.tmf_files = result.tmf_files
        record.checksums = result.checksums

        if not result.ok:
            missing_required = any(
                "Missing required" in e for e in result.errors
            )
            if missing_required:
                record.required_user_action = "; ".join(result.errors)
                self._set(record, State.WAITING_FOR_REQUIRED_FILES)
                return
            # Other validation errors (corrupt file, unreadable) -> attention.
            record.required_user_action = "; ".join(result.errors)
            self._set(record, State.NEEDS_ATTENTION)
            return

        # Assign the real (content-based) product id -> dedup identity.
        # Rekey the store so no stale "pending-*" duplicate is left behind.
        new_id = product_id_for(record.folder_name, record.checksums)
        if record.product_id != new_id:
            old_id = record.product_id
            record.product_id = new_id
            self.store.rekey(old_id, record)

    def _prepare_product(self, record: ProductRecord, folder: Path) -> None:
        self._set(record, State.PREPARING_PRODUCT)
        result = validate(folder)  # re-read for a typed ValidationResult
        previous_wiki = (record.metadata or {}).get("WIKI_KF2")
        record.fact_card = product_analyzer.build_fact_card(folder, result, self.config)
        record.metadata = metadata_generator.generate(folder, result, record.fact_card, self.config)
        if self.config.get("wiki.enabled", False):
            match = None
            if isinstance(previous_wiki, dict):
                try:
                    match = wiki_client.WikiMatch(
                        title=str(previous_wiki["title"]),
                        description=str(previous_wiki.get("description", "")),
                        path=str(previous_wiki["path"]),
                        url=str(previous_wiki["url"]),
                        excerpt=str(previous_wiki.get("excerpt", "")),
                        score=float(previous_wiki.get("score", 1.0)),
                    )
                except (KeyError, TypeError, ValueError):
                    match = None
            if match is None:
                match = wiki_client.WikiKF2Client(self.config).find(folder.name)
            if match is not None:
                record.metadata = wiki_client.enrich_metadata(record.metadata, match)

        base = package_builder.workspace(self.config.work_folder, record.product_id)
        package_builder.copy_sources(folder, base, record.metadata.get("RENAMED_FILES", {}))
        package_builder.write_listing(base, record.metadata)
        package_builder.write_readme_and_license(base, record.metadata,
                                                 self.config.get("brand.name", "WorkShop3D"))
        record.package_path = str(base)

    def _prepare_media(self, record: ProductRecord) -> None:
        self._set(record, State.PREPARING_MEDIA)
        base = Path(record.package_path)
        # Use the first PNG copy in work/files as the presentation image.
        files_dir = base / "files"
        pngs = sorted(files_dir.glob("*.png"))
        formats = ["STL"] + (["GLB"] if record.glb_files else []) + (["3MF"] if record.tmf_files else [])
        if pngs:
            if self.config.get("brand.render_graphics", True):
                coll = record.fact_card.get("collection")
                record.media = brand_renderer.render(
                    pngs[0], base / "media",
                    title=record.metadata.get("TITLE", record.folder_name),
                    brand=self.config.get("brand.name", "WorkShop3D"),
                    formats=formats,
                    collection=coll.get("display_name") if coll else None,
                    font_path=self.config.resolve_path(
                        "brand.font_path", "assets/fonts/UncialAntiqua-Regular.ttf"
                    ),
                    logo_path=self.config.resolve_path(
                        "brand.logo_path", "assets/brand/workshop3d_logo.png"
                    ),
                    patron_name=self.config.get("brand.patron_name", "KF2.pl"),
                    patron_logo_path=self.config.resolve_path(
                        "brand.patron_logo_path", "assets/brand/kf2_logo.png"
                    ),
                )
            else:
                # Branding disabled: the delivered PNGs are already the final
                # marketing images (user brands them with an external tool).
                # Copy them verbatim into media/.
                import shutil
                media_dir = base / "media"
                media_dir.mkdir(parents=True, exist_ok=True)
                record.media = []
                for i, png in enumerate(pngs):
                    dest = media_dir / ("cover.png" if i == 0 else png.name)
                    shutil.copy2(png, dest)
                    record.media.append(str(dest))
        # Build the sales ZIP.
        zip_path = package_builder.build_zip(base, record.metadata.get("ZIP_NAME", "package.zip"))
        record.media.append(zip_path)

    def _sync_clouds(self, record: ProductRecord) -> None:
        if not cloud_sync.enabled(self.config):
            record.cloud_sync = {}
            return
        self._set(record, State.SYNCING_CLOUDS)
        record.cloud_sync = cloud_sync.sync_product(record, self.config)
        self.store.upsert(record)

    def _publish(self, record: ProductRecord) -> None:
        self._set(record, State.PUBLISHING)
        publication_manager.publish_stores(record, self.config, record.package_path or "")
        if publication_manager.has_live_listing(record):
            self._set(record, State.PUBLISHED)

    def _promote(self, record: ProductRecord) -> None:
        if record.state != State.PUBLISHED.value:
            return
        # Finish every store attempt first.  Social posts should carry the
        # final working product link/store tags and must not compete with four
        # upload forms for the one paired Chrome worker.
        if any(
            result.get("status") in ("BROWSER_QUEUED", "READY_FOR_REVIEW", "SUBMITTED")
            for result in record.stores.values()
        ):
            return
        self._set(record, State.PROMOTING)
        publication_manager.promote_social(record, self.config, record.package_path or "")

    def _finish(self, record: ProductRecord) -> None:
        record.links, record.main_link = link_manager.build_link_card(record, self.config)

        store_statuses = [r.get("status") for r in record.stores.values()]
        published_any = any(s in ("PUBLISHED", "DRY_RUN") for s in store_statuses)
        staged_any = any(s == "STAGED" for s in store_statuses)  # handed to Thangs Sync etc.
        browser_any = any(s in ("BROWSER_QUEUED", "READY_FOR_REVIEW", "SUBMITTED")
                          for s in store_statuses)
        social_statuses = [r.get("status") for r in record.social.values()]
        social_browser_any = any(
            s in ("BROWSER_QUEUED", "READY_FOR_REVIEW", "SUBMITTED")
            for s in social_statuses
        )
        browser_any = browser_any or social_browser_any
        failed_any = any(s in ("FAILED", "NOT_CONNECTED", "NEEDS_ATTENTION") for s in store_statuses)
        social_failed_any = any(
            s in ("FAILED", "NOT_CONNECTED", "NEEDS_ATTENTION")
            for s in social_statuses
        )
        failed_any = failed_any or social_failed_any
        clouds_waiting = cloud_sync.enabled(self.config) and not cloud_sync.succeeded(record.cloud_sync)

        actions: list[str] = []
        if staged_any:
            actions.append("Open Thangs Sync and press Start Upload to finish publishing to Thangs.")
        if browser_any:
            if self.config.get("browser.auto_submit", False):
                actions.append(
                    "Chrome kończy sklepy i media społecznościowe automatycznie. Nic nie klikaj; "
                    "program zatrzyma się tylko wtedy, gdy strona pokaże CAPTCHA, "
                    "logowanie albo nowe obowiązkowe pole."
                )
            else:
                actions.append(
                    "Chrome wypełnił formularz. Kliknij publikację w otwartej karcie sklepu."
                )
        if clouds_waiting:
            # The message names the legs actually in use: without Google Drive
            # for desktop the working area is the local drop folder.
            actions.append(
                (record.cloud_sync or {}).get("message")
                or "Czekam na kopię w chmurze; ponowię automatycznie."
            )

        if browser_any:
            final = State.AWAITING_BROWSER_REVIEW
        elif clouds_waiting:
            final = State.AWAITING_CLOUD_SYNC
        elif failed_any and not (published_any or staged_any):
            final = State.NEEDS_ATTENTION
            actions.append("No store accepted the product. Check adapter status/credentials.")
        elif staged_any or failed_any:
            # Something went live or was staged, but not everything is fully done.
            final = State.COMPLETED_WITH_WARNINGS
        elif published_any:
            final = State.COMPLETED
        else:
            final = State.COMPLETED  # nothing enabled but pipeline ran cleanly

        # A product leaves the queue only after the store phase and both cloud
        # copies are ready. The same folder is moved on both sides to the
        # sibling "Opublikowane" directory, with no numbered duplicate.
        if (
            final in (State.COMPLETED, State.COMPLETED_WITH_WARNINGS)
            and cloud_sync.enabled(self.config)
        ):
            if not cloud_sync.archived(record.cloud_archive):
                record.cloud_archive = cloud_sync.archive_product(record, self.config)
                self.store.upsert(record)
            if not cloud_sync.archived(record.cloud_archive):
                final = State.AWAITING_CLOUD_SYNC
                actions.append(
                    (record.cloud_archive or {}).get("message")
                    or "Czekam na przeniesienie folderu do Opublikowane."
                )

        record.required_user_action = " ".join(actions) if actions else None

        if final in (State.COMPLETED, State.COMPLETED_WITH_WARNINGS):
            record.completed_at = datetime.now().timestamp()
        self._set(record, final)

        if record.package_path:
            report.build_report(record, Path(record.package_path) / "reports")
        title = record.metadata.get("TITLE", record.folder_name)
        success_statuses = {"PUBLISHED", "DRY_RUN"} if self.config.dry_run else {"PUBLISHED"}
        published = sum(result.get("status") in success_statuses for result in record.stores.values())
        total = len(self.config.enabled_stores())
        social_posted = sum(
            result.get("status") == "POSTED" for result in record.social.values()
        )
        social_total = len(self.config.enabled_social())
        if final in (State.COMPLETED, State.COMPLETED_WITH_WARNINGS):
            finished = datetime.fromtimestamp(record.completed_at).strftime("%H:%M")
            suffix = " — część wymaga uwagi" if final == State.COMPLETED_WITH_WARNINGS else ""
            notification_service.notify(
                f"WorkShop3D: GOTOWE{suffix}",
                f"{title}: {published}/{total} sklepów, {social_posted}/{social_total} social, "
                f"koniec {finished}. "
                "Google + Nextcloud: folder w Opublikowane. "
                "Możesz sprawdzić ofertę w panelu.",
            )
        elif final == State.NEEDS_ATTENTION:
            notification_service.notify(
                "WorkShop3D: potrzebna pomoc",
                f"{title}: automat zatrzymał się i pokazuje przyczynę w panelu.",
            )

    # -- helper -------------------------------------------------------------
    def _set(self, record: ProductRecord, state: State) -> None:
        record.state = state.value
        step = PROGRESS_STEP_BY_STATE.get(state)
        if step is not None:
            record.progress_step = max(record.progress_step, step)
        record.progress_total = PROGRESS_TOTAL
        self.store.upsert(record)
