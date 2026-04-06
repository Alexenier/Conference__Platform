import pytest


def get_participant_id(client, participant_token):
    return client.get("/auth/me", headers={"Authorization": f"Bearer {participant_token}"}).json()["id"]


def get_conference_id(client, admin_token):
    resp = client.post(
        "/conferences/",
        json={"title": "Conf for submissions", "submission_deadline": "2027-01-01T00:00:00"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    return resp.json()["id"]


def create_submission(client, participant_token, admin_token):
    user_id = get_participant_id(client, participant_token)
    conf_id = get_conference_id(client, admin_token)
    resp = client.post(
        "/submissions/",
        json={
            "conference_id": conf_id,
            "author_id": user_id,
            "title": "Test Submission",
            "abstract": "Test abstract",
            "section": "Інтелектуальні системи",
            "authors": [{"full_name": "Author", "organization": "Org", "email": "a@a.com", "is_presenter": True, "order": 0}]
        },
        headers={"Authorization": f"Bearer {participant_token}"}
    )
    return resp.json()["id"]


def test_create_submission_as_participant(client, participant_token, admin_token):
    user_id = get_participant_id(client, participant_token)
    conf_id = get_conference_id(client, admin_token)
    response = client.post(
        "/submissions/",
        json={
            "conference_id": conf_id,
            "author_id": user_id,
            "title": "My Submission",
            "abstract": "Abstract",
            "section": "Інтелектуальні системи",
            "authors": []
        },
        headers={"Authorization": f"Bearer {participant_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "draft"


def test_participant_sees_only_own_submissions(client, participant_token, admin_token):
    # Створюємо заявку як учасник
    create_submission(client, participant_token, admin_token)

    response = client.get(
        "/submissions/",
        headers={"Authorization": f"Bearer {participant_token}"}
    )
    assert response.status_code == 200
    submissions = response.json()
    user_id = get_participant_id(client, participant_token)
    for s in submissions:
        assert s["author_id"] == user_id


def test_org_sees_all_submissions(client, org_token):
    response = client.get(
        "/submissions/",
        headers={"Authorization": f"Bearer {org_token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_submit_draft_to_submitted(client, participant_token, admin_token):
    sub_id = create_submission(client, participant_token, admin_token)
    response = client.patch(
        f"/submissions/{sub_id}/status",
        json={"status": "submitted"},
        headers={"Authorization": f"Bearer {participant_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "submitted"


def test_fsm_invalid_transition(client, participant_token, org_token, admin_token):
    # Створюємо і подаємо заявку
    sub_id = create_submission(client, participant_token, admin_token)
    client.patch(
        f"/submissions/{sub_id}/status",
        json={"status": "submitted"},
        headers={"Authorization": f"Bearer {participant_token}"}
    )
    # Орг. комітет приймає
    client.patch(
        f"/submissions/{sub_id}/status",
        json={"status": "under_review"},
        headers={"Authorization": f"Bearer {org_token}"}
    )
    client.patch(
        f"/submissions/{sub_id}/status",
        json={"status": "accepted"},
        headers={"Authorization": f"Bearer {org_token}"}
    )
    # Спроба повернути в чернетку — має бути 422
    response = client.patch(
        f"/submissions/{sub_id}/status",
        json={"status": "draft"},
        headers={"Authorization": f"Bearer {org_token}"}
    )
    assert response.status_code == 422


def test_participant_cannot_change_to_accepted(client, participant_token, admin_token):
    sub_id = create_submission(client, participant_token, admin_token)
    response = client.patch(
        f"/submissions/{sub_id}/status",
        json={"status": "accepted"},
        headers={"Authorization": f"Bearer {participant_token}"}
    )
    assert response.status_code == 403