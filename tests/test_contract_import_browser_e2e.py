from __future__ import annotations

import socket
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

import pytest
import uvicorn
from playwright.sync_api import Page, expect
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import current_user, get_db
from app.auth.passwords import hash_password
from app.db.base import Base
from app.db.models import (
    ParentContract, Permission, Person, Project, ProjectAccess, ProjectPerson,
    Role, RolePermission, User, UserRole,
)
from app.main import app


@pytest.fixture
def browser_app():
    """Run the real FastAPI app with an isolated in-memory SQLite database."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    now = datetime.now(timezone.utc)
    user = User(
        username="browser-import-admin",
        password_hash=hash_password("e2e-test-password"),
        display_name="Browser Import Admin",
        active=True,
        created_at=now,
        updated_at=now,
        version=1,
    )
    project = Project(
        code="IMPORT",
        contract_code="76",
        name="Browser Import Project",
        status="ACTIVE",
        timezone="Asia/Tehran",
        created_at=now,
        updated_at=now,
        version=1,
    )
    person = Person(
        first_name="Initial",
        last_name="Owner",
        created_at=now,
        updated_at=now,
        version=1,
        is_active=True,
    )
    role = Role(code="browser-import-admin", name="Browser Import Admin", active=True)
    permission = Permission(code="parent_contract.create", name="Create Parent Contract")
    db.add_all([user, project, person, role, permission])
    db.flush()
    db.add_all([
        RolePermission(role_id=role.id, permission_id=permission.id),
        UserRole(user_id=user.id, role_id=role.id, project_id=None),
        ProjectAccess(user_id=user.id, project_id=project.id, active=True, granted_at=now, version=1),
        ProjectPerson(
            project_id=project.id,
            person_id=person.id,
            active=True,
            created_at=now,
            updated_at=now,
        ),
    ])
    db.commit()

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    # Bind an available local port, then let Uvicorn serve the actual app and APIs.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if server.started:
            break
        try:
            with urlopen(base_url + "/health", timeout=0.3) as response:
                if response.status == 200:
                    break
        except Exception:
            time.sleep(0.1)
    else:
        server.should_exit = True
        thread.join(timeout=5)
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()
        pytest.fail("Uvicorn test server did not start")

    try:
        yield {"base_url": base_url, "project_id": project.id, "person_id": person.id, "db": db}
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_browser_contract_import_full_preview_correct_revalidate_confirm(browser_app, page: Page, tmp_path: Path):
    base_url = browser_app["base_url"]
    project_id = browser_app["project_id"]
    person_id = browser_app["person_id"]

    page.goto(base_url + "/portal/")
    page.get_by_label("نام کاربری").fill("browser-import-admin")
    page.get_by_label("گذرواژه").fill("e2e-test-password")
    page.get_by_role("button", name="ورود امن").click()

    import_nav = page.get_by_role("button", name="ورود گروهی قراردادها")
    expect(import_nav).to_be_visible()
    import_nav.click()
    page.locator("#projectId").fill(str(project_id))

    csv_file = tmp_path / "contracts.csv"
    csv_file.write_text(
        "suffix,initial_person_id,property_id\n"
        f"0123,{person_id},\n"
        f"0123,{person_id},\n",
        encoding="utf-8",
    )
    page.locator("#contractImportFile").set_input_files(str(csv_file))
    page.get_by_role("button", name="بارگذاری و پیش‌نمایش").click()

    expect(page.locator("#contractImportPreviewPanel")).to_be_visible()
    expect(page.locator("#contractImportMeta")).to_contain_text("دارای خطا: 2")
    expect(page.locator("#contractImportConfirm")).to_be_disabled()

    # Correct the duplicate suffix through the actual browser input.
    page.get_by_label("پسوند قرارداد، ردیف 3").fill("0124")
    expect(page.locator("#contractImportConfirm")).to_be_disabled()
    page.get_by_role("button", name="اعتبارسنجی مجدد پس از اصلاح").click()

    expect(page.locator("#contractImportMeta")).to_contain_text("معتبر: 2")
    expect(page.locator("#contractImportConfirm")).to_be_enabled()
    expect(page.locator("#contractImportRows")).to_contain_text("760123")
    expect(page.locator("#contractImportRows")).to_contain_text("760124")

    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="تأیید و ثبت همه قراردادها").click()

    expect(page.locator("#contractImportMeta")).to_contain_text("ثبت موفق: 2 قرارداد")
    assert list(
        browser_app["db"].scalars(
            select(ParentContract.contract_number).order_by(ParentContract.contract_number)
        )
    ) == ["760123", "760124"]
