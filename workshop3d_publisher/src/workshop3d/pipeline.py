"""The product state machine (spec sections 4, 24).

Drives one product folder from DETECTED to a terminal state. Persists the
record after every transition so a restart resumes cleanly. Idempotent: it
never creates duplicate listings/posts and never modifies the originals.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from .config import Config
from .file_validator import validate
from .models import ProductRecord, State
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
        completed = record.state in (State.COMPLETED.value, State.COMPLETED_WITH_WARNINGS.value)
        if completed and current.checksums == record.checksums:
            return record  # nothing new -> no duplicate work
        # Files changed (e.g. GLB/3MF added) or not yet finished -> (re)process.
        record.folder_path = str(folder)
        return self.run(record)

    def run(self, record: ProductRecord) -> ProductRecord:
        """Advance a product as far as possible. Safe to call repeatedly.

        Idempotency across re-runs is guaranteed downstream: a store/social
        platform already PUBLISHED/POSTED is never published again.
        """
        folder = Path(record.folder_path)
        record.attempts += 1

        try:
            self._validate(record, folder)
            if record.state == State.WAITING_FOR_REQUIRED_FILES.value:
                return record

            self._prepare_product(record, folder)
            self._prepare_media(record)
            self._set(record, State.READY_TO_PUBLISH)

            self._publish(record)
            self._promote(record)
            self._finish(record)
        except Exception as exc:  # unexpected -> FAILED, but keep progress
            record.error_history.append(str(exc))
            self._set(record, State.FAILED)
            notification_service.notify("WorkShop3D: FAILED", f"{record.folder_name}: {exc}")
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
        record.fact_card = product_analyzer.build_fact_card(folder, result, self.config)
        record.metadata = metadata_generator.generate(folder, result, record.fact_card, self.config)

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
            coll = record.fact_card.get("collection")
            record.media = brand_renderer.render(
                pngs[0], base / "media",
                title=record.metadata.get("TITLE", record.folder_name),
                brand=self.config.get("brand.name", "WorkShop3D"),
                formats=formats,
                collection=coll.get("display_name") if coll else None,
            )
        # Build the sales ZIP.
        zip_path = package_builder.build_zip(base, record.metadata.get("ZIP_NAME", "package.zip"))
        record.media.append(zip_path)

    def _publish(self, record: ProductRecord) -> None:
        self._set(record, State.PUBLISHING)
        publication_manager.publish_stores(record, self.config, record.package_path or "")
        if publication_manager.has_live_listing(record):
            self._set(record, State.PUBLISHED)

    def _promote(self, record: ProductRecord) -> None:
        if record.state != State.PUBLISHED.value:
            return
        self._set(record, State.PROMOTING)
        publication_manager.promote_social(record, self.config, record.package_path or "")

    def _finish(self, record: ProductRecord) -> None:
        record.links, record.main_link = link_manager.build_link_card(record, self.config)

        store_statuses = [r.get("status") for r in record.stores.values()]
        published_any = any(s in ("PUBLISHED", "DRY_RUN") for s in store_statuses)
        failed_any = any(s in ("FAILED", "NOT_CONNECTED", "NEEDS_ATTENTION") for s in store_statuses)

        if published_any and not failed_any:
            final = State.COMPLETED
        elif published_any and failed_any:
            final = State.COMPLETED_WITH_WARNINGS
        elif not published_any and failed_any:
            final = State.NEEDS_ATTENTION
            record.required_user_action = "No store accepted the product. Check adapter status/credentials."
        else:
            final = State.COMPLETED  # nothing enabled but pipeline ran cleanly

        self._set(record, final)

        if record.package_path:
            report.build_report(record, Path(record.package_path) / "reports")
        notification_service.notify(
            f"WorkShop3D: {final.value}",
            f"{record.metadata.get('TITLE', record.folder_name)} -> {record.main_link or 'no link'}",
        )

    # -- helper -------------------------------------------------------------
    def _set(self, record: ProductRecord, state: State) -> None:
        record.state = state.value
        self.store.upsert(record)
