"""Pure validation and formatting rules for Parent Contract identifiers.

These helpers deliberately do not allocate database sequences or mutate records.
"""
from __future__ import annotations

import re

BUYER_TRANSFEREE_ROLE_CODE = "BUYER_TRANSFEREE"

_PROJECT_CODE = re.compile(r"^[1-9][0-9]$")
_SUFFIX = re.compile(r"^[0-9]{4}$")
_PARENT_NUMBER = re.compile(r"^[1-9][0-9]{5}$")


def validate_project_contract_code(value: str) -> str:
    """Return a valid two-digit project contract code (10..99)."""
    if not isinstance(value, str) or not _PROJECT_CODE.fullmatch(value):
        raise ValueError("project_contract_code_invalid")
    return value


def validate_parent_contract_suffix(value: str) -> str:
    """Return a four-digit suffix while preserving leading zeroes."""
    if not isinstance(value, str) or not _SUFFIX.fullmatch(value):
        raise ValueError("parent_contract_suffix_invalid")
    return value


def build_parent_contract_number(project_code: str, suffix: str) -> str:
    """Build the stable six-digit business number without integer conversion."""
    return validate_project_contract_code(project_code) + validate_parent_contract_suffix(suffix)


def validate_parent_contract_number(value: str) -> str:
    """Validate a six-digit Parent Contract number and preserve its string form."""
    if not isinstance(value, str) or not _PARENT_NUMBER.fullmatch(value):
        raise ValueError("parent_contract_number_invalid")
    if value[:2] < "10":
        raise ValueError("parent_contract_project_code_invalid")
    return value


def build_child_contract_number(parent_number: str, sequence: int) -> str:
    """Format a child transfer number; allocation must be handled transactionally elsewhere."""
    parent = validate_parent_contract_number(parent_number)
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise ValueError("transfer_sequence_invalid")
    return f"{parent}/{sequence}"
