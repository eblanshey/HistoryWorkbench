# File responsibility: Defines the Settings dataclass containing user
# configuration for the workbench including excluded types, properties,
# type-specific property exclusions, and the git executable path.
"""Settings data models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """User configuration for the workbench."""

    excluded_types: list[str]
    excluded_properties: list[str]
    excluded_properties_by_type: dict[str, list[str]]
    float_precision: int = 2  # Decimal places for float comparison and display
    git_executable: str = ""  # Path to the git executable; empty means search PATH
