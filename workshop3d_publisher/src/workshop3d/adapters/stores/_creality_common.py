"""Shared logic for the Creality Cloud adapters (EU + CN).

Creality Cloud has no public upload API. Its official bulk path is the
**Model File Batch Upload Tool** (a desktop app that uploads models from a
folder, one subfolder per model). This adapter therefore runs in "batch" mode:
it stages the product's files into a subfolder of a configured staging folder
and writes a human-readable metadata sheet (creality_upload_info.txt) you can
review/paste in the tool. The official tool (logged in as you) performs the
upload. A "browser" mode is kept as an alternative.

The adapter never logs in for you, never bypasses CAPTCHA/2FA, and never fakes
a completed upload -- it reports STAGED and asks you to run the tool.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from ..base import StoreAdapter
from ...models import ProductRecord, StoreResult

_ILLEGAL = '\\/:*?"<>|'
# Formats accepted by the Creality Cloud batch tool (+ our PNG preview).
_EXTS = (".stl", ".obj", ".ply", ".off", ".3mf", ".3ds", ".wrl", ".dae",
         ".step", ".stp", ".glb", ".png")


def _safe(name: str) -> str:
    cleaned = "".join("_" if ch in _ILLEGAL else ch for ch in name).strip()
    return cleaned or "model"


class CrealityBatchAdapter(StoreAdapter):
    """Base Creality adapter; subclasses set key / region_url / profile_env."""

    region_url = "https://www.crealitycloud.com"
    profile_env = "CREALITY_BROWSER_PROFILE"

    def _mode(self) -> str:
        return str(self.settings.get("mode", "batch"))

    def credentials_present(self) -> bool:
        if self._mode() == "browser":
            return bool(os.environ.get(self.profile_env))
        return bool(self.settings.get("staging_folder"))

    def publish(self, record: ProductRecord, workspace: str) -> StoreResult:
        meta = record.metadata
        title = meta.get("TITLE", record.folder_name)

        if self.config.dry_run:
            return StoreResult(
                platform=self.key, status="DRY_RUN",
                url=f"{self.region_url}/model-detail/DRYRUN",
                message="DRY_RUN: files staged for the Creality Batch Upload Tool (not uploaded).",
            )

        if self._mode() == "browser":
            if not os.environ.get(self.profile_env):
                return StoreResult(platform=self.key, status="NOT_CONNECTED",
                                   message=f"No logged-in browser session (set {self.profile_env}).")
            return StoreResult(platform=self.key, status="NEEDS_ATTENTION",
                               message="Browser automation requires manual confirmation. See README.")

        return self._stage(record, workspace, title)

    # -- batch (staging) mode ----------------------------------------------
    def _stage(self, record: ProductRecord, workspace: str, title: str) -> StoreResult:
        folder = self.settings.get("staging_folder")
        if not folder:
            return StoreResult(
                platform=self.key, status="NOT_CONNECTED",
                message=("Set stores." + self.key + ".staging_folder to the folder you "
                         "point the Creality Cloud Batch Upload Tool at."),
            )
        root = Path(folder)
        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return StoreResult(platform=self.key, status="FAILED",
                               message=f"Cannot use Creality staging folder: {exc}")

        model_dir = root / _safe(title)
        model_dir.mkdir(parents=True, exist_ok=True)

        files_dir = Path(workspace) / "files"
        copied = 0
        if files_dir.exists():
            for p in sorted(files_dir.glob("*")):
                if p.suffix.lower() in _EXTS:
                    shutil.copy2(p, model_dir / p.name)
                    copied += 1
        if copied == 0:
            return StoreResult(platform=self.key, status="FAILED",
                               message="No model/image files found to stage for Creality.")

        self._write_info(model_dir, record.metadata)
        return StoreResult(
            platform=self.key, status="STAGED",
            url=f"{self.region_url}/",
            message=(f"Staged {copied} files in '{model_dir.name}'. Open the Creality Cloud "
                     f"Batch Upload Tool, point it at '{root}', review the metadata "
                     "(creality_upload_info.txt) and upload."),
        )

    def _write_info(self, model_dir: Path, meta: dict) -> None:
        lic = meta.get("LICENSE_SUMMARY", {})
        lines = [
            f"Title: {meta.get('TITLE', '')}",
            "",
            f"Category: {meta.get('CATEGORY', '')}",
            "",
            "Tags: " + ", ".join(meta.get("TAGS", [])),
            "",
            "Description:",
            "",
            meta.get("DESCRIPTION_EN", ""),
            "",
            f"License: {lic.get('summary', '')} (owner: {lic.get('owner', 'WorkShop3D')})",
            "",
            "Files:",
        ]
        lines += [f"  - {f}" for f in meta.get("INCLUDED_FILES", [])]
        (model_dir / "creality_upload_info.txt").write_text("\n".join(lines), encoding="utf-8")
