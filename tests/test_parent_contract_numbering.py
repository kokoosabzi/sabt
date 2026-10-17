import pytest

from app.contracts.numbering import (
    build_child_contract_number,
    build_parent_contract_number,
    validate_parent_contract_number,
    validate_project_contract_code,
)


@pytest.mark.parametrize("code", ["10", "17", "76", "99"])
def test_project_contract_code_accepts_two_digit_codes_starting_at_ten(code):
    assert validate_project_contract_code(code) == code


@pytest.mark.parametrize("code", ["01", "09", "00", "1", "100", "AA", "", None])
def test_project_contract_code_rejects_invalid_values(code):
    with pytest.raises(ValueError, match="project_contract_code_invalid"):
        validate_project_contract_code(code)


def test_parent_contract_number_preserves_leading_zero_suffix():
    assert build_parent_contract_number("76", "0123") == "760123"
    assert build_parent_contract_number("10", "0000") == "100000"


@pytest.mark.parametrize("suffix", ["123", "12345", "12A4", "", None])
def test_parent_contract_suffix_must_be_exactly_four_digits(suffix):
    with pytest.raises(ValueError, match="parent_contract_suffix_invalid"):
        build_parent_contract_number("76", suffix)


@pytest.mark.parametrize("number", ["010123", "090123", "76123", "7612345", "76AB23", "", None])
def test_parent_contract_number_rejects_invalid_values(number):
    with pytest.raises(ValueError):
        validate_parent_contract_number(number)


def test_child_contract_number_is_formatted_without_zero_padding():
    assert build_child_contract_number("760123", 1) == "760123/1"
    assert build_child_contract_number("760123", 10) == "760123/10"


@pytest.mark.parametrize("sequence", [0, -1, True, 1.5, "2", None])
def test_child_contract_number_requires_positive_integer_sequence(sequence):
    with pytest.raises(ValueError, match="transfer_sequence_invalid"):
        build_child_contract_number("760123", sequence)
