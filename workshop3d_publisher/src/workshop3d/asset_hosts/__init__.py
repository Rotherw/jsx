"""Asset-host package. Importing it registers all built-in hosts."""
from . import static, google_drive  # noqa: F401
from .base import AssetHost, AssetHostError, get_asset_host, register_host  # noqa: F401
