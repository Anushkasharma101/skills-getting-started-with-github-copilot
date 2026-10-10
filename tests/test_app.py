import copy
import uuid

import pytest
from fastapi.testclient import TestClient

from src import app as app_module
from src.app import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset the in-memory activity store before and after every test."""
    original_activities = copy.deepcopy(app_module.activities)

    app_module.activities.clear()
    app_module.activities.update(copy.deepcopy(original_activities))
    yield
    app_module.activities.clear()
    app_module.activities.update(copy.deepcopy(original_activities))


def test_get_activities_lists_available_activities():
    # Arrange
    # No setup needed beyond the default in-memory activities store.

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    payload = response.json()
    assert "Chess Club" in payload
    assert "Programming Class" in payload
    assert "Gym Class" in payload
    assert isinstance(payload["Chess Club"]["participants"], list)


def test_signup_for_activity_adds_student():
    # Arrange
    activity_name = "Chess Club"
    email = f"{uuid.uuid4()}@example.com"
    before = list(app_module.activities[activity_name]["participants"])

    # Act
    response = client.post(f"/activities/{activity_name}/signup?email={email}")

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == f"Signed up {email} for {activity_name}"
    assert email in app_module.activities[activity_name]["participants"]
    assert len(app_module.activities[activity_name]["participants"]) == len(before) + 1


def test_signup_rejects_duplicate_email_without_changing_participants():
    # Arrange
    activity_name = "Chess Club"
    duplicate_email = "michael@mergington.edu"
    before = copy.deepcopy(app_module.activities[activity_name]["participants"])

    # Act
    response = client.post(f"/activities/{activity_name}/signup?email={duplicate_email}")

    # Assert
    assert response.status_code == 400
    assert "already signed up" in response.json()["detail"].lower()
    assert app_module.activities[activity_name]["participants"] == before


def test_signup_for_unknown_activity_returns_404():
    # Arrange
    activity_name = "Nonexistent Club"
    email = f"{uuid.uuid4()}@example.com"

    # Act
    response = client.post(f"/activities/{activity_name}/signup?email={email}")

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_for_activity_removes_student():
    # Arrange
    activity_name = "Gym Class"
    email = f"{uuid.uuid4()}@example.com"
    signup_response = client.post(f"/activities/{activity_name}/signup?email={email}")
    assert signup_response.status_code == 200

    # Act
    response = client.delete(f"/activities/{activity_name}/signup?email={email}")

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == f"Unregistered {email} from {activity_name}"
    assert email not in app_module.activities[activity_name]["participants"]


@pytest.mark.parametrize(
    "activity_name,email",
    [
        ("MISSING Club", "student@mergington.edu"),
        ("Chess Club", "not-signed-up@mergington.edu"),
    ],
)
def test_unregister_for_missing_activity_or_unregistered_student_returns_404(activity_name, email):
    # Arrange
    # The test data intentionally covers both a missing activity and a valid activity
    # where the requested email is not currently registered.

    # Act
    response = client.delete(f"/activities/{activity_name}/signup?email={email}")

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found" if activity_name not in app_module.activities else "Student is not signed up"
