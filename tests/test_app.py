from unittest.mock import patch

import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@patch("app.get_all_names", return_value=["Alice", "Bob"])
def test_index_returns_200(mock_names, client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Alice" in resp.data
    assert b"Bob" in resp.data


@patch("app.get_all_names", return_value=[])
def test_index_empty_list(mock_names, client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"<li>" not in resp.data


@patch("app.insert_user", return_value="fake_id")
@patch("app.get_all_names", return_value=["Alice"])
def test_add_user_success(mock_names, mock_insert, client):
    resp = client.post(
        "/add",
        json={"name": "Alice", "age": 30},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "Successfully inserted" in data["message"]


def test_add_user_missing_name(client):
    resp = client.post("/add", json={"age": 30})
    assert resp.status_code == 400
    assert "Name is required" in resp.get_json()["error"]


def test_add_user_invalid_age(client):
    resp = client.post("/add", json={"name": "Alice", "age": "abc"})
    assert resp.status_code == 400
    assert "integer" in resp.get_json()["error"]


def test_add_user_age_out_of_range(client):
    resp = client.post("/add", json={"name": "Alice", "age": 200})
    assert resp.status_code == 400
    assert "between 0 and 150" in resp.get_json()["error"]


def test_add_user_bad_json(client):
    resp = client.post("/add", data="not json", content_type="text/plain")
    assert resp.status_code == 400