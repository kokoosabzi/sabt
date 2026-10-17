import csv
import io

import pytest
from openpyxl import Workbook

from app.contracts.import_service import (
    ContractImportError,
    MAX_UPLOAD_BYTES,
    parse_parent_contract_import,
)


def test_parse_csv_normalizes_rows_and_optional_property():
    content = b"suffix,initial_person_id,property_id\n0123,7,4\n0124,8,\n"
    rows = parse_parent_contract_import("contracts.csv", content)
    assert rows == [
        {"row_number": 2, "suffix": "0123", "initial_person_id": 7, "property_id": 4},
        {"row_number": 3, "suffix": "0124", "initial_person_id": 8, "property_id": None},
    ]


def test_parse_xlsx():
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["suffix", "initial_person_id", "property_id"])
    sheet.append(["0100", 12, None])
    buffer = io.BytesIO()
    workbook.save(buffer)
    rows = parse_parent_contract_import("contracts.xlsx", buffer.getvalue())
    assert rows[0]["suffix"] == "0100"
    assert rows[0]["initial_person_id"] == 12
    assert rows[0]["property_id"] is None


@pytest.mark.parametrize(
    ("filename", "content", "error"),
    [
        ("contracts.txt", b"suffix,initial_person_id\n1,2", "import_file_type_unsupported"),
        ("contracts.csv", b"suffix\n1", "import_required_columns_missing"),
        ("contracts.csv", b"suffix,initial_person_id\n0001,abc", "import_row_invalid:2"),
        ("contracts.csv", b"suffix,initial_person_id\n", "import_no_data_rows"),
    ],
)
def test_rejects_invalid_import_files(filename, content, error):
    with pytest.raises(ContractImportError, match=error):
        parse_parent_contract_import(filename, content)


def test_rejects_oversized_upload():
    with pytest.raises(ContractImportError, match="import_file_too_large"):
        parse_parent_contract_import("contracts.csv", b"x" * (MAX_UPLOAD_BYTES + 1))


def test_rejects_invalid_csv_encoding():
    with pytest.raises(ContractImportError, match="import_csv_encoding_invalid"):
        parse_parent_contract_import("contracts.csv", b"\xff\xfe\xff")
