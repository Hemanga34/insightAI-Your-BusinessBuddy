from conftest import register


def test_registration_login_and_workspace(client):
    headers = register(client, "OWNER@example.in")
    workspace = client.get("/api/workspace", headers=headers).json()
    assert workspace["currency"] == "INR"
    assert workspace["timezone"] == "Asia/Kolkata"
    assert workspace["email"] == "owner@example.in"
    response = client.post(
        "/api/auth/login",
        json={
            "email": "owner@example.in",
            "password": "a-long-test-password",
        },
    )
    assert response.status_code == 200
    assert (
        client.get("/api/workspace", headers={"Authorization": "Bearer invalid"}).status_code == 401
    )
    assert (
        client.post(
            "/api/auth/login",
            json={
                "email": "owner@example.in",
                "password": "incorrect-password",
            },
        ).status_code
        == 401
    )


def test_invalid_registration_and_duplicate_email(client):
    register(client)
    duplicate = client.post(
        "/api/auth/register",
        json={
            "email": "owner@example.in",
            "password": "a-long-test-password",
            "business_name": "Other",
        },
    )
    assert duplicate.status_code == 409
    assert (
        client.post(
            "/api/auth/register",
            json={
                "email": "bad-email",
                "password": "short",
                "business_name": "  ",
            },
        ).status_code
        == 422
    )
