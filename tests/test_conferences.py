import pytest

CONFERENCE_DATA = {
    "title": "Test Conference",
    "description": "Test description",
    "submission_deadline": "2027-01-01T00:00:00",
}


def test_create_conference_as_admin(client, admin_token):
    response = client.post(
        "/conferences/",
        json=CONFERENCE_DATA,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Conference"
    assert "id" in data


def test_create_conference_as_participant(client, participant_token):
    response = client.post(
        "/conferences/",
        json=CONFERENCE_DATA,
        headers={"Authorization": f"Bearer {participant_token}"}
    )
    assert response.status_code == 403


def test_create_conference_unauthorized(client):
    response = client.post("/conferences/", json=CONFERENCE_DATA)
    assert response.status_code == 401


def test_list_conferences(client):
    response = client.get("/conferences/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_update_conference_as_admin(client, admin_token):
    # Спочатку створюємо
    create_resp = client.post(
        "/conferences/",
        json=CONFERENCE_DATA,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    conf_id = create_resp.json()["id"]

    # Оновлюємо
    response = client.patch(
        f"/conferences/{conf_id}",
        json={"title": "Updated Title"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


def test_delete_conference_as_admin(client, admin_token):
    # Спочатку створюємо
    create_resp = client.post(
        "/conferences/",
        json=CONFERENCE_DATA,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    conf_id = create_resp.json()["id"]

    # Видаляємо
    response = client.delete(
        f"/conferences/{conf_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204


def test_delete_conference_as_participant(client, participant_token, admin_token):
    # Створюємо як адмін
    create_resp = client.post(
        "/conferences/",
        json=CONFERENCE_DATA,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    conf_id = create_resp.json()["id"]

    # Намагаємось видалити як учасник
    response = client.delete(
        f"/conferences/{conf_id}",
        headers={"Authorization": f"Bearer {participant_token}"}
    )
    assert response.status_code == 403