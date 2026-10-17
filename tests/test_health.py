from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_management_portal_is_served_as_persian_rtl_html() -> None:
    response = TestClient(app).get("/portal/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'lang="fa" dir="rtl"' in response.text
    assert "پرتال مدیریتی SABT" in response.text
    assert "/reports/management/summary" in response.text
