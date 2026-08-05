"""Creality Cloud EU store adapter.

Batch mode (default): stages files + metadata for the Creality Cloud Batch
Upload Tool. Browser mode: reuse an existing logged-in session (never bypass
CAPTCHA/2FA, never store passwords). See _creality_common for the full flow.
"""
from __future__ import annotations

from ..base import register_store
from ._creality_common import CrealityBatchAdapter


@register_store
class CrealityCloudEUAdapter(CrealityBatchAdapter):
    key = "creality_cloud_eu"
    supports_formats = ("stl", "3mf")
    region_url = "https://www.crealitycloud.com"
    profile_env = "CREALITY_EU_BROWSER_PROFILE"
