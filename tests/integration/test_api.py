import asyncio
from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.asyncio


async def test_registration_login_and_profile(async_client, account):
    user, headers = await account("Student@example.com")
    assert user["email"] == "student@example.com"
    assert user["role"] == "USER"
    assert "hashed_password" not in user

    profile = await async_client.get("/auth/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json() == user

    login = await async_client.post(
        "/auth/login", json={"email": user["email"], "password": "incorrect123"}
    )
    assert login.status_code == 401
    assert login.headers["WWW-Authenticate"] == "Bearer"


async def test_duplicate_email_under_concurrent_registration(async_client):
    payload = {"email": "duplicate@example.com", "password": "secure123", "name": "Test User"}
    results = await asyncio.gather(
        async_client.post("/auth/register", json=payload),
        async_client.post("/auth/register", json={**payload, "email": "Duplicate@example.com"}),
    )
    assert sorted(response.status_code for response in results) == [200, 409]


async def test_validation_errors_do_not_return_passwords(async_client):
    response = await async_client.post(
        "/auth/register", json={"email": "broken-address", "password": "x9!Zq7#", "name": " "}
    )
    assert response.status_code == 422
    assert {error["loc"][-1] for error in response.json()["detail"]} == {
        "email",
        "password",
        "name",
    }
    assert "x9!Zq7#" not in response.text
    assert all("input" not in error for error in response.json()["detail"])

    response = await async_client.post(
        "/auth/register",
        json={
            "email": "student@example.com",
            "password": "я" * 37,
            "name": "Student",
            "role": "ADMIN",
        },
    )
    assert response.status_code == 422
    assert {error["loc"][-1] for error in response.json()["detail"]} == {"password", "role"}


async def test_authentication_is_required(async_client):
    for headers in ({}, {"Authorization": "Bearer invalid-token"}):
        response = await async_client.get("/tasks", headers=headers)
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_task_lifecycle_and_email(async_client, account, smtp_messages):
    user, headers = await account("owner@example.com")
    response = await async_client.post(
        "/tasks",
        headers=headers,
        json={"title": "Написать API", "description": "FastAPI", "deadline": "2026-12-01T00:00:00"},
    )
    assert response.status_code == 200, response.text
    task = response.json()
    path = f"/tasks/{task['id']}"
    assert task["user_id"] == user["id"]
    assert task["status"] == "pending"
    assert task["priority"] == "medium"
    assert datetime.fromisoformat(task["deadline"]) == datetime(2026, 12, 1, tzinfo=UTC)

    fetched = await async_client.get(path, headers=headers)
    assert fetched.status_code == 200
    assert fetched.json() == task

    assert len(smtp_messages) == 1
    assert smtp_messages[0]["To"] == user["email"]
    assert "Написать API" in smtp_messages[0].get_content()

    edited = await async_client.put(
        path, headers=headers, json={"status": "in_progress", "deadline": None}
    )
    assert edited.status_code == 200
    assert edited.json()["status"] == "in_progress"
    assert edited.json()["title"] == task["title"]
    assert edited.json()["description"] == task["description"]
    assert edited.json()["deadline"] is None

    deleted = await async_client.delete(path, headers=headers)
    assert deleted.status_code == 204
    assert not deleted.content
    assert (await async_client.get(path, headers=headers)).status_code == 404


async def test_task_filters_pagination_and_invalid_fields(async_client, account):
    _, headers = await account("owner@example.com")
    for title, status, priority in [
        ("first", "done", "high"),
        ("second", "pending", "high"),
        ("third", "done", "high"),
        ("fourth", "done", "low"),
    ]:
        response = await async_client.post(
            "/tasks", headers=headers, json={"title": title, "status": status, "priority": priority}
        )
        assert response.status_code == 200

    response = await async_client.get(
        "/tasks",
        headers=headers,
        params={"status": "done", "priority": "high", "limit": 1, "offset": 1},
    )
    assert response.status_code == 200
    assert [task["title"] for task in response.json()] == ["third"]
    assert (await async_client.get("/tasks?limit=0", headers=headers)).status_code == 422
    assert (await async_client.get("/tasks?status=invalid", headers=headers)).status_code == 422
    response = await async_client.post("/tasks", headers=headers, json={"title": "   "})
    assert response.status_code == 422
    tasks = (await async_client.get("/tasks", headers=headers)).json()
    response = await async_client.put(
        f"/tasks/{tasks[0]['id']}", headers=headers, json={"title": None}
    )
    assert response.status_code == 422


async def test_user_cannot_access_another_users_tasks(async_client, account):
    _, owner_headers = await account("owner@example.com")
    _, other_headers = await account("other@example.com")
    task = (
        await async_client.post("/tasks", json={"title": "Private"}, headers=owner_headers)
    ).json()
    path = f"/tasks/{task['id']}"

    assert (await async_client.get("/tasks", headers=other_headers)).json() == []
    assert (await async_client.get(path, headers=other_headers)).status_code == 404
    assert (
        await async_client.put(path, headers=other_headers, json={"status": "done"})
    ).status_code == 404
    assert (await async_client.delete(path, headers=other_headers)).status_code == 404
    assert (await async_client.get(path, headers=owner_headers)).json()["status"] == "pending"


async def test_admin_permissions_follow_current_database_role(async_client, account):
    _, admin_headers = await account("admin@example.com", admin=True)
    user, user_headers = await account("member@example.com")
    task = (
        await async_client.post("/tasks", headers=user_headers, json={"title": "Review"})
    ).json()
    path = f"/tasks/{task['id']}"
    role_path = f"/admin/users/{user['id']}/role"

    assert (await async_client.get("/admin/users", headers=user_headers)).status_code == 403
    denied = await async_client.put(role_path, headers=user_headers, json={"role": "ADMIN"})
    assert denied.status_code == 403

    listed = await async_client.get("/admin/users", headers=admin_headers)
    assert {entry["role"] for entry in listed.json()} == {"USER", "ADMIN"}
    all_tasks = await async_client.get("/tasks", headers=admin_headers)
    assert [entry["id"] for entry in all_tasks.json()] == [task["id"]]
    assert (await async_client.get(path, headers=admin_headers)).status_code == 200
    updated = await async_client.put(path, headers=admin_headers, json={"status": "done"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "done"
    assert (await async_client.delete(path, headers=admin_headers)).status_code == 204

    promoted = await async_client.put(role_path, headers=admin_headers, json={"role": "ADMIN"})
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "ADMIN"
    assert (await async_client.get("/admin/users", headers=user_headers)).status_code == 200

    demoted = await async_client.put(role_path, headers=admin_headers, json={"role": "USER"})
    assert demoted.status_code == 200
    assert (await async_client.get("/admin/users", headers=user_headers)).status_code == 403
    absent = await async_client.put(
        "/admin/users/100000/role", headers=admin_headers, json={"role": "ADMIN"}
    )
    assert absent.status_code == 404


async def test_docs_and_database_health(async_client):
    assert (await async_client.get("/docs")).status_code == 200
    assert (await async_client.get("/healthz")).json() == {"status": "ok"}


async def test_oauth2_form_login_and_openapi(async_client, account):
    user, _ = await account("student@example.com")
    response = await async_client.post(
        "/auth/login",
        data={"username": user["email"], "password": "secure123", "grant_type": "password"},
    )
    assert response.status_code == 200
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert (await async_client.get("/auth/profile", headers=headers)).json()["id"] == user["id"]

    invalid = await async_client.post(
        "/auth/login",
        data={"username": user["email"], "password": "secure123", "grant_type": "other"},
    )
    assert invalid.status_code == 422
    malformed = await async_client.post(
        "/auth/login", content="{", headers={"Content-Type": "application/json"}
    )
    assert malformed.status_code == 422

    schema = (await async_client.get("/openapi.json")).json()
    oauth2 = schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]
    assert oauth2["flows"]["password"]["tokenUrl"] == "auth/login"
    bodies = schema["paths"]["/auth/login"]["post"]["requestBody"]["content"]
    assert set(bodies) == {"application/json", "application/x-www-form-urlencoded"}


async def test_previously_issued_id_token_still_authenticates(async_client, account, app):
    from src.core.security import create_access_token

    user, _ = await account("student@example.com")
    token = create_access_token({"sub": str(user["id"])}, app.state.settings)
    response = await async_client.get("/auth/profile", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["id"] == user["id"]


async def test_uow_rolls_back_all_changes_on_error(async_client, account, app):
    from sqlalchemy import func, select

    from src.models.task import Task
    from src.models.user import User
    from src.utils.unit_of_work import UnitOfWork

    user, _ = await account("student@example.com")
    async with app.state.session_factory() as session:
        with pytest.raises(RuntimeError):
            async with UnitOfWork(session) as uow:
                saved_user = await uow.users.get_by_id(user["id"])
                await uow.users.update(saved_user, {"name": "Changed"})
                await uow.tasks.create({"title": "Uncommitted", "user_id": user["id"]})
                raise RuntimeError("Abort transaction")

    async with app.state.session_factory() as session:
        assert (await session.get(User, user["id"])).name == user["name"]
        assert await session.scalar(select(func.count()).select_from(Task)) == 0


async def test_failed_commit_does_not_send_email(
    async_client, account, app, monkeypatch, smtp_messages
):
    from sqlalchemy import func, select

    from src.models.task import Task
    from src.utils.unit_of_work import UnitOfWork

    _, headers = await account("student@example.com")

    async def failed_commit(self):
        raise RuntimeError("Commit failed")

    monkeypatch.setattr(UnitOfWork, "commit", failed_commit)
    with pytest.raises(RuntimeError, match="Commit failed"):
        await async_client.post("/tasks", headers=headers, json={"title": "Uncommitted"})

    async with app.state.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Task)) == 0
    assert smtp_messages == []
