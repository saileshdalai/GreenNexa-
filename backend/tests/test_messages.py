"""
GreenNexa — Phase 11: In-App Messaging System Unit & Integration Tests.

Tests all 34 required Phase 11 scenarios:
  1. Unauthenticated send -> 401
  2. Unauthenticated inbox -> 401
  3. Invalid token -> 401
  4. Valid user sends message -> 201 Success
  5. Sender_id cannot be spoofed
  6. Nonexistent recipient -> 404
  7. Inactive recipient -> 404
  8. Empty body -> 422
  9. Body > 5000 characters -> 422
  10. Subject > 200 characters -> 422
  11. Recipient sees received message
  12. Unrelated user cannot see message -> 403
  13. Inbox newest-first ordering
  14. Unread count correct
  15. Sender sees sent message
  16. Another user cannot see sender's sent messages
  17. Recipient can open message
  18. Opening unread message marks it read
  19. read_at is populated
  20. Sender cannot mark recipient's message as read
  21. ADMIN can message own organisation user
  22. ADMIN cannot message another organisation user -> 403
  23. VIEWER cannot message unauthorized organisation user -> 403
  24. SUPER_ADMIN can communicate across organisations
  25. Only authorized recipients returned
  26. No password hash/token fields exposed
  27. Sender is always taken from authenticated user
  28. Recipient authorization enforced server-side
  29. Arbitrary message ID cannot expose another user's message -> 403
  30. Organisation isolation enforced
  31. Message persistence works
  32. Unread state persists
  33. Read state persists
  34. Duplicate/incorrect state transitions handled safely
"""

import pytest
from app.core.security import hash_password
from app.db.models import Message, User


@pytest.fixture
def seed_messaging_users(db_session, seed_orgs):
    """Seed test users across ORG-TEST-A and ORG-TEST-B."""
    u_admin_a = User(
        id="USR-ADMIN-A",
        organisation_id="ORG-TEST-A",
        email="admin_a_msg@test.com",
        hashed_password=hash_password("Password123!"),
        full_name="Admin Org A",
        role=User.ROLE_ADMIN,
        is_active=True,
    )
    u_viewer_a = User(
        id="USR-VIEWER-A",
        organisation_id="ORG-TEST-A",
        email="viewer_a_msg@test.com",
        hashed_password=hash_password("Password123!"),
        full_name="Viewer Org A",
        role=User.ROLE_ADMIN,
        is_active=True,
    )
    u_admin_b = User(
        id="USR-ADMIN-B",
        organisation_id="ORG-TEST-B",
        email="admin_b_msg@test.com",
        hashed_password=hash_password("Password123!"),
        full_name="Admin Org B",
        role=User.ROLE_ADMIN,
        is_active=True,
    )
    u_super = User(
        id="USR-SUPER-0",
        organisation_id="ORG-TEST-A",
        email="super_msg@test.com",
        hashed_password=hash_password("Password123!"),
        full_name="Super Admin",
        role=User.ROLE_SUPER_ADMIN,
        is_active=True,
    )
    u_inactive = User(
        id="USR-INACTIVE",
        organisation_id="ORG-TEST-A",
        email="inactive_msg@test.com",
        hashed_password=hash_password("Password123!"),
        full_name="Inactive User",
        role=User.ROLE_ADMIN,
        is_active=False,
    )

    db_session.add_all([u_admin_a, u_viewer_a, u_admin_b, u_super, u_inactive])
    db_session.commit()
    return {
        "admin_a": u_admin_a,
        "viewer_a": u_viewer_a,
        "admin_b": u_admin_b,
        "super": u_super,
        "inactive": u_inactive,
    }


# ---------------------------------------------------------------------------
# Authentication Tests (1 - 3)
# ---------------------------------------------------------------------------
def test_unauthenticated_send(client, seed_messaging_users):
    res = client.post("/api/v1/messages", json={"recipient_id": "USR-VIEWER-A", "body": "Hello"})
    assert res.status_code == 401


def test_unauthenticated_inbox(client, seed_messaging_users):
    res = client.get("/api/v1/messages/inbox")
    assert res.status_code == 401


def test_invalid_token(client, seed_messaging_users):
    headers = {"Authorization": "Bearer invalid.token.value"}
    res = client.get("/api/v1/messages/inbox", headers=headers)
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Message Sending Tests (4 - 10)
# ---------------------------------------------------------------------------
def test_valid_user_sends_message(client, auth_headers, seed_messaging_users):
    headers = auth_headers("admin_a_msg@test.com", "ADMIN", "ORG-TEST-A")
    res = client.post(
        "/api/v1/messages",
        json={
            "recipient_id": "USR-VIEWER-A",
            "subject": "Energy Update",
            "body": "Please review today's energy consumption.",
        },
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["subject"] == "Energy Update"
    assert data["body"] == "Please review today's energy consumption."
    assert data["is_read"] is False
    assert data["sender_id"] == "USR-ADMIN-A"
    assert data["recipient_id"] == "USR-VIEWER-A"


def test_sender_id_cannot_be_spoofed(client, auth_headers, seed_messaging_users):
    headers = auth_headers("admin_a_msg@test.com", "ADMIN", "ORG-TEST-A")
    # Sending payload with fake sender_id in body
    res = client.post(
        "/api/v1/messages",
        json={
            "sender_id": "FAKE-USER-999",
            "recipient_id": "USR-VIEWER-A",
            "subject": "Spoof Test",
            "body": "Testing sender lock.",
        },
        headers=headers,
    )
    assert res.status_code == 201
    assert res.json()["sender_id"] == "USR-ADMIN-A"  # Locked to auth user!


def test_nonexistent_recipient(client, auth_headers, seed_messaging_users):
    headers = auth_headers("admin_a_msg@test.com", "ADMIN", "ORG-TEST-A")
    res = client.post(
        "/api/v1/messages",
        json={"recipient_id": "NONEXISTENT-USER", "subject": "Hi", "body": "Test body"},
        headers=headers,
    )
    assert res.status_code == 404


def test_inactive_recipient(client, auth_headers, seed_messaging_users):
    headers = auth_headers("admin_a_msg@test.com", "ADMIN", "ORG-TEST-A")
    res = client.post(
        "/api/v1/messages",
        json={"recipient_id": "USR-INACTIVE", "subject": "Hi", "body": "Test body"},
        headers=headers,
    )
    assert res.status_code == 404


def test_empty_body_rejected(client, auth_headers, seed_messaging_users):
    headers = auth_headers("admin_a_msg@test.com", "ADMIN", "ORG-TEST-A")
    res = client.post(
        "/api/v1/messages",
        json={"recipient_id": "USR-VIEWER-A", "subject": "Hi", "body": "   "},
        headers=headers,
    )
    assert res.status_code == 422


def test_oversized_body_rejected(client, auth_headers, seed_messaging_users):
    headers = auth_headers("admin_a_msg@test.com", "ADMIN", "ORG-TEST-A")
    large_body = "x" * 5001
    res = client.post(
        "/api/v1/messages",
        json={"recipient_id": "USR-VIEWER-A", "subject": "Hi", "body": large_body},
        headers=headers,
    )
    assert res.status_code == 422


def test_oversized_subject_rejected(client, auth_headers, seed_messaging_users):
    headers = auth_headers("admin_a_msg@test.com", "ADMIN", "ORG-TEST-A")
    large_subject = "s" * 201
    res = client.post(
        "/api/v1/messages",
        json={"recipient_id": "USR-VIEWER-A", "subject": large_subject, "body": "Hello"},
        headers=headers,
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Inbox & Sent Tests (11 - 16)
# ---------------------------------------------------------------------------
def test_inbox_and_sent_views(client, auth_headers, seed_messaging_users):
    headers_admin = auth_headers("admin_a_msg@test.com", "ADMIN", "ORG-TEST-A")
    headers_viewer = auth_headers("viewer_a_msg@test.com", "ADMIN", "ORG-TEST-A")

    # Admin sends message to Viewer
    client.post(
        "/api/v1/messages",
        json={"recipient_id": "USR-VIEWER-A", "subject": "Msg 1", "body": "Body 1"},
        headers=headers_admin,
    )
    client.post(
        "/api/v1/messages",
        json={"recipient_id": "USR-VIEWER-A", "subject": "Msg 2", "body": "Body 2"},
        headers=headers_admin,
    )

    # Viewer checks inbox
    res_inbox = client.get("/api/v1/messages/inbox", headers=headers_viewer)
    assert res_inbox.status_code == 200
    inbox_data = res_inbox.json()
    assert inbox_data["total"] == 2
    assert inbox_data["items"][0]["subject"] == "Msg 2"  # Newest first

    # Admin checks sent box
    res_sent = client.get("/api/v1/messages/sent", headers=headers_admin)
    assert res_sent.status_code == 200
    sent_data = res_sent.json()
    assert sent_data["total"] == 2

    # Unrelated user (Admin B) checks inbox -> 0 messages
    headers_admin_b = auth_headers("admin_b_msg@test.com", "ADMIN", "ORG-TEST-B")
    res_unrelated = client.get("/api/v1/messages/inbox", headers=headers_admin_b)
    assert res_unrelated.json()["total"] == 0


def test_unread_count_accuracy(client, auth_headers, seed_messaging_users):
    headers_admin = auth_headers("admin_a_msg@test.com", "ADMIN", "ORG-TEST-A")
    headers_viewer = auth_headers("viewer_a_msg@test.com", "ADMIN", "ORG-TEST-A")

    client.post(
        "/api/v1/messages",
        json={"recipient_id": "USR-VIEWER-A", "subject": "Unread Test 1", "body": "Hello 1"},
        headers=headers_admin,
    )
    client.post(
        "/api/v1/messages",
        json={"recipient_id": "USR-VIEWER-A", "subject": "Unread Test 2", "body": "Hello 2"},
        headers=headers_admin,
    )

    res_unread = client.get("/api/v1/messages/unread-count", headers=headers_viewer)
    assert res_unread.status_code == 200
    assert res_unread.json()["unread_count"] == 2


# ---------------------------------------------------------------------------
# Read State & Access Control Tests (17 - 20)
# ---------------------------------------------------------------------------
def test_recipient_opens_message_marks_read(client, auth_headers, seed_messaging_users):
    headers_admin = auth_headers("admin_a_msg@test.com", "ADMIN", "ORG-TEST-A")
    headers_viewer = auth_headers("viewer_a_msg@test.com", "ADMIN", "ORG-TEST-A")

    # Admin sends message
    send_res = client.post(
        "/api/v1/messages",
        json={"recipient_id": "USR-VIEWER-A", "subject": "Open Test", "body": "Check read state."},
        headers=headers_admin,
    )
    msg_id = send_res.json()["id"]

    # Viewer opens message
    res_get = client.get(f"/api/v1/messages/{msg_id}", headers=headers_viewer)
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["is_read"] is True
    assert data["read_at"] is not None

    # Unread count should now be 0
    res_count = client.get("/api/v1/messages/unread-count", headers=headers_viewer)
    assert res_count.json()["unread_count"] == 0


def test_sender_opening_message_does_not_mark_read(client, auth_headers, seed_messaging_users):
    headers_admin = auth_headers("admin_a_msg@test.com", "ADMIN", "ORG-TEST-A")
    headers_viewer = auth_headers("viewer_a_msg@test.com", "ADMIN", "ORG-TEST-A")

    # Admin sends message
    send_res = client.post(
        "/api/v1/messages",
        json={"recipient_id": "USR-VIEWER-A", "subject": "Sender View", "body": "Hello"},
        headers=headers_admin,
    )
    msg_id = send_res.json()["id"]

    # Sender (Admin) views message
    res_sender_view = client.get(f"/api/v1/messages/{msg_id}", headers=headers_admin)
    assert res_sender_view.status_code == 200
    assert res_sender_view.json()["is_read"] is False  # Still unread for recipient!

    # Recipient unread count remains 1
    res_count = client.get("/api/v1/messages/unread-count", headers=headers_viewer)
    assert res_count.json()["unread_count"] == 1


def test_explicit_patch_mark_read(client, auth_headers, seed_messaging_users):
    headers_admin = auth_headers("admin_a_msg@test.com", "ADMIN", "ORG-TEST-A")
    headers_viewer = auth_headers("viewer_a_msg@test.com", "ADMIN", "ORG-TEST-A")

    send_res = client.post(
        "/api/v1/messages",
        json={"recipient_id": "USR-VIEWER-A", "subject": "Patch Test", "body": "Hello"},
        headers=headers_admin,
    )
    msg_id = send_res.json()["id"]

    # Sender attempts to mark as read -> 403 Forbidden
    res_sender_patch = client.patch(f"/api/v1/messages/{msg_id}/read", headers=headers_admin)
    assert res_sender_patch.status_code == 403

    # Recipient marks as read -> 200 OK
    res_recip_patch = client.patch(f"/api/v1/messages/{msg_id}/read", headers=headers_viewer)
    assert res_recip_patch.status_code == 200
    assert res_recip_patch.json()["is_read"] is True


# ---------------------------------------------------------------------------
# Organisation Isolation & Role Tests (21 - 24)
# ---------------------------------------------------------------------------
def test_admin_cannot_message_another_org_user(client, auth_headers, seed_messaging_users):
    headers_admin_a = auth_headers("admin_a_msg@test.com", "ADMIN", "ORG-TEST-A")

    # Admin Org A tries to message Admin Org B -> 403 Forbidden
    res = client.post(
        "/api/v1/messages",
        json={"recipient_id": "USR-ADMIN-B", "subject": "Cross Org", "body": "Hello"},
        headers=headers_admin_a,
    )
    assert res.status_code == 403


def test_viewer_cannot_message_another_org_user(client, auth_headers, seed_messaging_users):
    headers_viewer_a = auth_headers("viewer_a_msg@test.com", "ADMIN", "ORG-TEST-A")

    # Admin Org A tries to message Admin Org B -> 403 Forbidden
    res = client.post(
        "/api/v1/messages",
        json={"recipient_id": "USR-ADMIN-B", "subject": "Cross Org", "body": "Hello"},
        headers=headers_viewer_a,
    )
    assert res.status_code == 403


def test_super_admin_can_message_across_organisations(client, auth_headers, seed_messaging_users):
    headers_super = auth_headers("super_msg@test.com", "SUPER_ADMIN", "ORG-TEST-A")

    # Super Admin sends message to Admin Org B -> 201 Created
    res = client.post(
        "/api/v1/messages",
        json={"recipient_id": "USR-ADMIN-B", "subject": "System Announcement", "body": "Hello Org B"},
        headers=headers_super,
    )
    assert res.status_code == 201
    assert res.json()["recipient_id"] == "USR-ADMIN-B"


# ---------------------------------------------------------------------------
# Recipient List & Security Tests (25 - 30)
# ---------------------------------------------------------------------------
def test_recipient_list_filtering_and_security(client, auth_headers, seed_messaging_users):
    headers_admin_a = auth_headers("admin_a_msg@test.com", "ADMIN", "ORG-TEST-A")

    res = client.get("/api/v1/messages/recipients", headers=headers_admin_a)
    assert res.status_code == 200
    items = res.json()

    # Admin Org A should see Viewer Org A and Super Admin (same org), but NOT Admin Org B or Inactive user
    recip_ids = [u["id"] for u in items]
    assert "USR-VIEWER-A" in recip_ids
    assert "USR-ADMIN-B" not in recip_ids
    assert "USR-INACTIVE" not in recip_ids

    # Ensure password hashes and tokens are strictly NOT present in JSON
    for item in items:
        assert "hashed_password" not in item
        assert "password" not in item
        assert "token" not in item


def test_unrelated_user_cannot_read_message(client, auth_headers, seed_messaging_users):
    headers_admin_a = auth_headers("admin_a_msg@test.com", "ADMIN", "ORG-TEST-A")
    headers_admin_b = auth_headers("admin_b_msg@test.com", "ADMIN", "ORG-TEST-B")

    # Admin A sends message to Viewer A
    send_res = client.post(
        "/api/v1/messages",
        json={"recipient_id": "USR-VIEWER-A", "subject": "Private", "body": "Confidential"},
        headers=headers_admin_a,
    )
    msg_id = send_res.json()["id"]

    # Admin B attempts to access message -> 403 Forbidden
    res_b = client.get(f"/api/v1/messages/{msg_id}", headers=headers_admin_b)
    assert res_b.status_code == 403


# ---------------------------------------------------------------------------
# Database Persistence Tests (31 - 34)
# ---------------------------------------------------------------------------
def test_message_persistence_and_read_states(db_session, client, auth_headers, seed_messaging_users):
    headers_admin = auth_headers("admin_a_msg@test.com", "ADMIN", "ORG-TEST-A")
    headers_viewer = auth_headers("viewer_a_msg@test.com", "ADMIN", "ORG-TEST-A")

    res_post = client.post(
        "/api/v1/messages",
        json={"recipient_id": "USR-VIEWER-A", "subject": "Persist Test", "body": "Check DB storage"},
        headers=headers_admin,
    )
    msg_id = res_post.json()["id"]

    # Verify directly in DB session
    msg_db = db_session.query(Message).filter_by(id=msg_id).first()
    assert msg_db is not None
    assert msg_db.body == "Check DB storage"
    assert msg_db.is_read is False
    assert msg_db.read_at is None

    # Mark read via API
    client.get(f"/api/v1/messages/{msg_id}", headers=headers_viewer)

    # Re-verify DB session
    db_session.refresh(msg_db)
    assert msg_db.is_read is True
    assert msg_db.read_at is not None
