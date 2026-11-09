from fastapi.testclient import TestClient

from app.main import app


def test_contract_import_portal_exposes_inline_correction_and_revalidation():
    response = TestClient(app).get("/portal/")
    assert response.status_code == 200
    assert "contractImportRevalidate" in response.text
    assert "اعتبارسنجی مجدد پس از اصلاح" in response.text
    assert "contracts/parent/import/validate" in response.text
    assert "تأیید و ثبت همه قراردادها" in response.text


def test_contract_search_and_bulk_import_use_koko_ui_primitives_without_losing_dom_hooks():
    response = TestClient(app).get("/portal/")
    assert response.status_code == 200
    html = response.text
    for hook in ("contractPage", "contractForm", "contractNumber", "contractResult",
                 "contractSummary", "contractRows", "contractPrint",
                 "contractImportPage", "contractImportFile", "contractImportPreview",
                 "contractImportRevalidate", "contractImportConfirm",
                 "contractImportMeta", "contractImportIssues",
                 "contractImportPreviewPanel", "contractImportRows"):
        assert f'id="{hook}"' in html
    assert 'koko-form-section' in html
    assert 'class="koko-form-actions"' in html
    assert 'class="koko-table-wrap"' in html
    assert 'class="koko-table"' in html
    assert 'accept=".csv,.xlsx"' in html
    assert 'type="button" disabled' in html
