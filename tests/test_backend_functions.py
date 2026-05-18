from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import PyMongoError

import app as chirptown


class FakeUsersCollection:
    def __init__(self, user=None, should_raise=False):
        self.user = user
        self.should_raise = should_raise

    def find_one(self, query, projection=None):
        if self.should_raise:
            raise PyMongoError("database unavailable")

        if self.user and query.get("username") == self.user.get("username"):
            if projection:
                return {key: self.user[key] for key in projection if key in self.user}
            return self.user

        return None


def response_json(response_tuple):
    response, status_code = response_tuple
    return response.get_json(), status_code


def test_redact_mongo_uri_masks_passwords_only_when_credentials_exist():
    assert (
        chirptown.redact_mongo_uri("mongodb://user:secret@database:27017/microblog")
        == "mongodb://user:***@database:27017/microblog"
    )
    assert (
        chirptown.redact_mongo_uri("mongodb://database:27017/microblog")
        == "mongodb://database:27017/microblog"
    )


def test_validate_username_accepts_only_allowed_public_usernames():
    assert chirptown.validate_username("abc") is None
    assert chirptown.validate_username("user_123") is None
    assert chirptown.validate_username("") == "Username is required."
    assert chirptown.validate_username(None) == "Username is required."
    assert chirptown.validate_username("ab") is not None
    assert chirptown.validate_username("a" * 21) is not None
    assert chirptown.validate_username("bad-name") is not None
    assert chirptown.validate_username("bad name") is not None
    assert chirptown.validate_username("bad@email") is not None


def test_serialize_datetime_normalizes_datetime_values_to_utc_strings():
    aware = datetime(2026, 5, 18, 10, 30, tzinfo=timezone.utc)
    naive = datetime(2026, 5, 18, 10, 30)

    assert chirptown.serialize_datetime(None) is None
    assert chirptown.serialize_datetime(aware) == "2026-05-18T10:30:00Z"
    assert chirptown.serialize_datetime(naive) == "2026-05-18T10:30:00Z"
    assert chirptown.serialize_datetime("already text") == "already text"


def test_serialize_user_exposes_safe_profile_fields_only():
    user = {
        "username": "alice",
        "password": "hashed-password",
        "bio": "Cloud learner",
        "created_at": datetime(2026, 5, 18, tzinfo=timezone.utc),
    }

    serialized = chirptown.serialize_user(user)

    assert serialized == {
        "username": "alice",
        "bio": "Cloud learner",
        "created_at": "2026-05-18T00:00:00Z",
    }
    assert "password" not in serialized


def test_serialize_user_defaults_missing_bio_to_empty_string():
    serialized = chirptown.serialize_user(
        {"username": "alice", "created_at": datetime(2026, 5, 18, tzinfo=timezone.utc)}
    )

    assert serialized["bio"] == ""


def test_serialize_tweet_exposes_public_tweet_fields_and_like_state():
    tweet_id = ObjectId()
    tweet = {
        "_id": tweet_id,
        "content": "hello",
        "author": "alice",
        "created_at": datetime(2026, 5, 18, tzinfo=timezone.utc),
        "likes": 2,
        "liked_by": ["alice", "bob"],
        "internal_note": "do not leak",
    }

    serialized = chirptown.serialize_tweet(tweet, viewer_username="bob")

    assert serialized == {
        "id": str(tweet_id),
        "content": "hello",
        "author": "alice",
        "created_at": "2026-05-18T00:00:00Z",
        "likes": 2,
        "liked_by_current_user": True,
    }
    assert "liked_by" not in serialized
    assert "internal_note" not in serialized


def test_serialize_tweet_defaults_missing_or_invalid_optional_fields():
    tweet_id = ObjectId()

    serialized = chirptown.serialize_tweet({"_id": tweet_id, "liked_by": "alice"})

    assert serialized["id"] == str(tweet_id)
    assert serialized["content"] == ""
    assert serialized["author"] == "Unknown User"
    assert serialized["created_at"] is None
    assert serialized["likes"] == 0
    assert serialized["liked_by_current_user"] is False


def test_token_helpers_round_trip_and_reject_bad_tokens():
    token = chirptown.make_token("alice")

    assert chirptown.username_from_token(token) == "alice"
    assert chirptown.username_from_token("not-a-real-token") is None


def test_tweet_object_id_parses_valid_ids_and_rejects_invalid_values():
    object_id = ObjectId()

    assert chirptown.tweet_object_id(str(object_id)) == object_id
    assert chirptown.tweet_object_id("invalid") is None
    assert chirptown.tweet_object_id(None) is None


def test_api_response_returns_consistent_success_envelope():
    with chirptown.app.app_context():
        payload, status_code = response_json(
            chirptown.api_response(
                data={"answer": 42},
                message="Created",
                http_status=201,
            )
        )

    assert status_code == 201
    assert payload == {
        "status": "success",
        "message": "Created",
        "data": {"answer": 42},
    }


def test_error_response_returns_consistent_error_envelope():
    with chirptown.app.app_context():
        payload, status_code = response_json(chirptown.error_response("Nope", 403))

    assert status_code == 403
    assert payload == {"status": "error", "message": "Nope"}


def test_request_payload_reads_json_body():
    with chirptown.app.test_request_context(
        "/anything",
        method="POST",
        json={"content": "hello"},
    ):
        assert chirptown.request_payload() == {"content": "hello"}


def test_request_payload_reads_form_body():
    with chirptown.app.test_request_context(
        "/anything",
        method="POST",
        data={"content": "hello"},
    ):
        assert chirptown.request_payload() == {"content": "hello"}


def test_request_payload_treats_invalid_json_as_empty_payload():
    with chirptown.app.test_request_context(
        "/anything",
        method="POST",
        data="{broken",
        content_type="application/json",
    ):
        assert chirptown.request_payload() == {}


def test_bearer_token_extracts_only_bearer_auth_values():
    token = chirptown.make_token("alice")

    with chirptown.app.test_request_context(
        "/anything",
        headers={"Authorization": f"Bearer {token}"},
    ):
        assert chirptown.bearer_token() == token

    with chirptown.app.test_request_context(
        "/anything",
        headers={"Authorization": f"Token {token}"},
    ):
        assert chirptown.bearer_token() is None

    with chirptown.app.test_request_context("/anything"):
        assert chirptown.bearer_token() is None


def test_current_username_returns_none_without_usable_token(monkeypatch):
    monkeypatch.setattr(
        chirptown,
        "users_collection",
        FakeUsersCollection({"username": "alice"}),
    )

    with chirptown.app.test_request_context("/anything"):
        assert chirptown.current_username() is None

    with chirptown.app.test_request_context(
        "/anything",
        headers={"Authorization": "Bearer invalid"},
    ):
        assert chirptown.current_username() is None


def test_current_username_returns_user_for_valid_token(monkeypatch):
    token = chirptown.make_token("alice")
    monkeypatch.setattr(
        chirptown,
        "users_collection",
        FakeUsersCollection({"username": "alice", "bio": "hello"}),
    )

    with chirptown.app.test_request_context(
        "/anything",
        headers={"Authorization": f"Bearer {token}"},
    ):
        assert chirptown.current_username() == "alice"


def test_current_username_returns_none_when_token_user_is_missing(monkeypatch):
    token = chirptown.make_token("missing")
    monkeypatch.setattr(chirptown, "users_collection", FakeUsersCollection(None))

    with chirptown.app.test_request_context(
        "/anything",
        headers={"Authorization": f"Bearer {token}"},
    ):
        assert chirptown.current_username() is None


def test_current_username_returns_none_when_lookup_fails(monkeypatch):
    token = chirptown.make_token("alice")
    monkeypatch.setattr(chirptown, "users_collection", FakeUsersCollection(should_raise=True))

    with chirptown.app.test_request_context(
        "/anything",
        headers={"Authorization": f"Bearer {token}"},
    ):
        assert chirptown.current_username() is None


def test_require_auth_returns_user_when_authenticated(monkeypatch):
    token = chirptown.make_token("alice")
    monkeypatch.setattr(
        chirptown,
        "users_collection",
        FakeUsersCollection({"username": "alice"}),
    )

    with chirptown.app.test_request_context(
        "/anything",
        headers={"Authorization": f"Bearer {token}"},
    ):
        username, error = chirptown.require_auth()

    assert username == "alice"
    assert error is None


def test_require_auth_returns_401_error_tuple_when_unauthenticated():
    with chirptown.app.test_request_context("/anything"):
        username, error = chirptown.require_auth()
        payload, status_code = response_json(error)

    assert username is None
    assert status_code == 401
    assert payload == {"status": "error", "message": "Authentication required."}


def test_add_cors_headers_allows_origin_and_auth_headers():
    with chirptown.app.test_request_context(
        "/anything",
        headers={"Origin": "http://localhost"},
    ):
        response = chirptown.app.response_class("")
        response = chirptown.add_cors_headers(response)

    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost"
    assert "Authorization" in response.headers["Access-Control-Allow-Headers"]
    assert "POST" in response.headers["Access-Control-Allow-Methods"]
    assert response.headers["Vary"] == "Origin"


def test_add_cors_headers_falls_back_to_wildcard_without_origin():
    with chirptown.app.test_request_context("/anything"):
        response = chirptown.app.response_class("")
        response = chirptown.add_cors_headers(response)

    assert response.headers["Access-Control-Allow-Origin"] == "*"
