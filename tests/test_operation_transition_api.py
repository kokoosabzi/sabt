from fastapi.testclient import TestClient

from app.main import app


def test_operation_transition_route_is_registered() -> None:
    route = next(
        route for route in app.routes
        if getattr(route, "path", None) == "/operations/{operation_id}/transition"
    )
    assert "POST" in route.methods


def test_operation_transition_requires_authentication() -> None:
    response = TestClient(app).post(
        "/operations/1/transition",
        json={"target_state": "IN_PROGRESS", "expected_version": 1},
    )
    assert response.status_code == 401
