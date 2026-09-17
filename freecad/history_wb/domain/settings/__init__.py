# Module responsibility: Settings subdomain containing configuration models
# and repository interface for user preferences.
"""Settings domain module."""

from .models import Settings
from .persistence_state import (
    ByTypeSettingState,
    ListSettingState,
    SettingsPersistenceState,
    normalize_git_executable,
)
from .repository import SettingsPersistenceRepository, SettingsRepository
from .text_codec import (
    parse_by_type_lines,
    parse_list_lines,
    serialize_by_type_lines,
    serialize_list_lines,
)


__all__ = [
    "Settings",
    "SettingsRepository",
    "SettingsPersistenceRepository",
    "ListSettingState",
    "ByTypeSettingState",
    "SettingsPersistenceState",
    "normalize_git_executable",
    "parse_list_lines",
    "serialize_list_lines",
    "parse_by_type_lines",
    "serialize_by_type_lines",
]
