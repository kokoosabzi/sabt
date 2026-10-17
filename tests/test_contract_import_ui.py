from fastapi.testclient import TestClient

from app.main import app


def test_contract_import_portal_exposes_inline_correction_and_revalidation():
    response = TestClient(app).get("/portal/")
    assert response.status_code == 200
    assert "contractImportRevalidate" in response.text
    assert "اعتبارسنجی مجدد پس از اصلاح" in response.text
    assert "contracts/parent/import/validate" in response.text
    assert "تأیید و ثبت همه قراردادها" in response.text
