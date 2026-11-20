from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.passwords import hash_password
from app.bootstrap import create_initial_admin
from app.db.base import Base
from app.db.models import Person
from app.auth.dependencies import get_db
from app.main import app


@pytest.fixture()
def people_api_client():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    def override_get_db():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, engine
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _admin(client, engine):
    with Session(engine) as db:
        create_initial_admin(db, username='people.admin', display_name='People Admin', password='a secure people password')
        db.commit()
    login = client.post('/auth/login', auth=('people.admin', 'a secure people password'))
    assert login.status_code == 200
    return {'Authorization': 'Bearer ' + login.json()['access_token']}


def _project(client, headers, code, contract_code):
    response = client.post('/projects', headers=headers, json={
        'code': code, 'name': code, 'contract_code': contract_code, 'timezone': 'Asia/Tehran',
    })
    assert response.status_code == 201
    return response.json()['id']


def test_create_and_search_people_are_scoped_to_project(people_api_client):
    client, engine = people_api_client
    headers = _admin(client, engine)
    project_a = _project(client, headers, 'people-a', '76')
    project_b = _project(client, headers, 'people-b', '77')
    created = client.post('/people', headers=headers, json={
        'project_id': project_a, 'first_name': 'مریم', 'last_name': 'رضایی',
        'father_name': 'علی', 'national_id': '0012345678', 'mobile': '09120000000',
    })
    assert created.status_code == 201
    person = created.json()
    assert person['national_id'] == '0012345678'
    assert person['possible_duplicate_warning'] is False
    visible = client.get('/people', headers=headers, params={'project_id': project_a, 'q': 'رضایی'})
    hidden = client.get('/people', headers=headers, params={'project_id': project_b})
    assert visible.status_code == 200 and visible.json()['items'][0]['id'] == person['id']
    assert hidden.status_code == 200 and hidden.json()['items'] == []


def test_duplicate_national_id_warns_but_never_silently_merges(people_api_client):
    client, engine = people_api_client
    headers = _admin(client, engine)
    project_id = _project(client, headers, 'people-duplicates', '78')
    payload = {'project_id': project_id, 'first_name': 'Ali', 'last_name': 'One', 'national_id': '1234567890'}
    first = client.post('/people', headers=headers, json=payload)
    second = client.post('/people', headers=headers, json={**payload, 'last_name': 'Two'})
    assert first.status_code == 201 and second.status_code == 201
    assert second.json()['possible_duplicate_warning'] is True
    assert second.json()['possible_duplicate_ids'] == [first.json()['id']]
    assert second.json()['id'] != first.json()['id']
    with Session(engine) as db:
        assert db.scalar(select(Person.id).where(Person.id == first.json()['id'])) is not None
        assert db.scalar(select(Person.id).where(Person.id == second.json()['id'])) is not None


def test_existing_person_can_be_associated_with_another_project(people_api_client):
    client, engine = people_api_client
    headers = _admin(client, engine)
    project_a = _project(client, headers, 'people-link-a', '79')
    project_b = _project(client, headers, 'people-link-b', '80')
    created = client.post('/people', headers=headers, json={
        'project_id': project_a, 'first_name': 'Reused', 'last_name': 'Person',
    })
    person_id = created.json()['id']
    linked = client.post(f'/people/{person_id}/projects/{project_b}', headers=headers)
    assert linked.status_code == 200
    assert linked.json() == {'project_id': project_b, 'person_id': person_id, 'active': True}
    listed = client.get('/people', headers=headers, params={'project_id': project_b})
    assert [item['id'] for item in listed.json()['items']] == [person_id]


def test_people_api_requires_authentication_and_permission(people_api_client):
    client, engine = people_api_client
    assert client.get('/people', params={'project_id': 1}).status_code == 401
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        from app.db.models import User
        db.add(User(username='ordinary.people', password_hash=hash_password('ordinary people password'),
                    display_name='Ordinary', active=True, created_at=now, updated_at=now, version=1))
        db.commit()
    login = client.post('/auth/login', auth=('ordinary.people', 'ordinary people password'))
    assert login.status_code == 200
    headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
    denied = client.get('/people', headers=headers, params={'project_id': 1})
    assert denied.status_code == 403