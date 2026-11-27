import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.bootstrap import create_initial_admin
from app.db.base import Base
from app.db.models import Property
from app.auth.dependencies import get_db
from app.main import app


@pytest.fixture()
def properties_api_client():
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
        create_initial_admin(db, username='properties.admin', display_name='Properties Admin', password='a secure properties password')
        db.commit()
    login = client.post('/auth/login', auth=('properties.admin', 'a secure properties password'))
    assert login.status_code == 200
    return {'Authorization': 'Bearer ' + login.json()['access_token']}


def _project(client, headers, code, contract_code):
    response = client.post('/projects', headers=headers, json={
        'code': code, 'name': code, 'contract_code': contract_code, 'timezone': 'Asia/Tehran',
    })
    assert response.status_code == 201
    return response.json()['id']


def test_create_and_search_properties_are_scoped_to_project(properties_api_client):
    client, engine = properties_api_client
    headers = _admin(client, engine)
    project_a = _project(client, headers, 'properties-a', '76')
    project_b = _project(client, headers, 'properties-b', '77')
    created = client.post('/properties', headers=headers, json={
        'project_id': project_a, 'block_tower': 'A', 'floor': '3',
        'unit_number': '301', 'unit_code': 'A-301', 'plaque_number': '301',
        'address': 'Test address',
    })
    assert created.status_code == 201
    property_record = created.json()
    assert property_record['unit_code'] == 'A-301'
    assert property_record['possible_duplicate_warning'] is False
    visible = client.get('/properties', headers=headers, params={'project_id': project_a, 'q': 'A-301'})
    hidden = client.get('/properties', headers=headers, params={'project_id': project_b})
    assert visible.status_code == 200 and visible.json()['items'][0]['id'] == property_record['id']
    assert hidden.status_code == 200 and hidden.json()['items'] == []


def test_duplicate_property_identifiers_warn_but_never_silently_merge(properties_api_client):
    client, engine = properties_api_client
    headers = _admin(client, engine)
    project_id = _project(client, headers, 'properties-duplicates', '78')
    payload = {'project_id': project_id, 'unit_number': '12', 'unit_code': 'B-12'}
    first = client.post('/properties', headers=headers, json=payload)
    second = client.post('/properties', headers=headers, json=payload)
    assert first.status_code == 201 and second.status_code == 201
    assert second.json()['possible_duplicate_warning'] is True
    assert second.json()['possible_duplicate_ids'] == [first.json()['id']]
    assert second.json()['id'] != first.json()['id']
    with Session(engine) as db:
        assert db.scalar(select(Property.id).where(Property.id == first.json()['id'])) is not None
        assert db.scalar(select(Property.id).where(Property.id == second.json()['id'])) is not None


def test_existing_property_can_be_associated_with_another_project(properties_api_client):
    client, engine = properties_api_client
    headers = _admin(client, engine)
    project_a = _project(client, headers, 'properties-link-a', '79')
    project_b = _project(client, headers, 'properties-link-b', '80')
    created = client.post('/properties', headers=headers, json={
        'project_id': project_a, 'unit_number': '502', 'unit_code': 'LINK-502',
    })
    property_id = created.json()['id']
    linked = client.post(f'/properties/{property_id}/projects/{project_b}', headers=headers)
    assert linked.status_code == 200
    assert linked.json() == {'project_id': project_b, 'property_id': property_id, 'active': True}
    listed = client.get('/properties', headers=headers, params={'project_id': project_b})
    assert [item['id'] for item in listed.json()['items']] == [property_id]


def test_property_requires_identifier_and_authentication(properties_api_client):
    client, engine = properties_api_client
    assert client.get('/properties', params={'project_id': 1}).status_code == 401
    headers = _admin(client, engine)
    project_id = _project(client, headers, 'properties-required', '81')
    invalid = client.post('/properties', headers=headers, json={'project_id': project_id, 'address': 'Only address'})
    assert invalid.status_code == 422
    with Session(engine) as db:
        assert db.scalar(select(Property)) is None