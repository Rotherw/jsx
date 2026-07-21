"""Adapter package. Importing it registers every built-in store & social adapter."""
from . import stores, social  # noqa: F401
from .base import (  # noqa: F401
    StoreAdapter,
    SocialAdapter,
    get_store_adapter,
    get_social_adapter,
    register_store,
    register_social,
)
