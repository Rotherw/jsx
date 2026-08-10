"""Creality Cloud CN store adapter.

Same batch/browser flow as the EU adapter, targeting the CN region.
"""
from __future__ import annotations

from ..base import register_store
from ._creality_common import CrealityBatchAdapter


@register_store
class CrealityCloudCNAdapter(CrealityBatchAdapter):
    key = "creality_cloud_cn"
    supports_formats = ("stl", "3mf")
    region_url = "https://www.crealitycloud.cn"
    profile_env = "CREALITY_CN_BROWSER_PROFILE"
