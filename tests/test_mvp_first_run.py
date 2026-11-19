from datetime import datetime, timedelta, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth.dependencies import get_db
from app.auth.permission_catalog import PERMISSION_CATALOG
from app.bootstrap import create_initial_admin
from app.db.config import get_database_url
from app.main import app


ROOT = Path(__file__).resolve().parents[1]


def test_fresh_windows_style_database_admin_login_first_project_and_dashboard(
    tmp_path, monkeypatch
):
    data_directory = tmp_path / "SABT data"
    monkeypatch.setenv("SABT_DATA_DIR", str(data_directory))

    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    command.upgrade(config, "head")

    engine = create_engine(
        get_database_url(),
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    try:
        with Session(engine) as db:
            with db.begin():
                create_initial_admin(
                    db,
                    username="mvp.admin",
                    display_name="مدیر MVP",
                    password="a secure mvp administrator password",
                )

        def override_get_db():
            with Session(engine) as db:
                yield db

        app.dependency_overrides[get_db] = override_get_db
        try:
            with TestClient(app) as client:
                login = client.post(
                    "/auth/login",
                    auth=("mvp.admin", "a secure mvp administrator password"),
                )
                assert login.status_code == 200
                headers = {
                    "Authorization": f"Bearer {login.json()['access_token']}"
                }

                empty_projects = client.get("/projects", headers=headers)
                assert empty_projects.status_code == 200
                assert empty_projects.json()["total"] == 0

                created = client.post(
                    "/projects",
                    headers=headers,
                    json={
                        "code": "mvp-first-project",
                        "name": "پروژه آزمایشی MVP",
                        "contract_code": "76",
                        "timezone": "Asia/Tehran",
                    },
                )
                assert created.status_code == 201
                project_id = created.json()["id"]

                projects = client.get("/projects", headers=headers)
                assert projects.status_code == 200
                assert projects.json()["total"] == 1
                assert projects.json()["items"][0]["id"] == project_id

                context = client.get(
                    "/reports/project-context",
                    params={"project_id": project_id},
                    headers=headers,
                )
                assert context.status_code == 200
                assert context.json()["project"]["timezone"] == "Asia/Tehran"

                now = datetime.now(timezone.utc)
                dashboard = client.get(
                    "/reports/management/summary",
                    params={
                        "project_id": project_id,
                        "start_at": (now - timedelta(days=1)).isoformat(),
                        "end_at": (now + timedelta(days=1)).isoformat(),
                    },
                    headers=headers,
                )
                assert dashboard.status_code == 200
                assert dashboard.json()["project"]["id"] == project_id
                assert dashboard.json()["indicators"]["created_operations"] == 0
        finally:
            app.dependency_overrides.clear()
    finally:
        engine.dispose()
