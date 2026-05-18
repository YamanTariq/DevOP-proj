from datetime import datetime, timezone
import os
import re

from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "devops_secret_key")
app.config["MAX_TWEET_LENGTH"] = int(os.getenv("MAX_TWEET_LENGTH", "280"))
app.config["TOKEN_MAX_AGE_SECONDS"] = int(
    os.getenv("TOKEN_MAX_AGE_SECONDS", str(60 * 60 * 24 * 7))
)

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")
MAX_BIO_LENGTH = 180

MONGO_URI = os.getenv("MONGO_URI", "mongodb://database:27017/microblog")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "microblog")

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    socketTimeoutMS=10000,
)
db = client.get_database(MONGO_DB_NAME)
tweets_collection = db.tweets
users_collection = db.users
token_serializer = URLSafeTimedSerializer(app.secret_key, salt="chirptown-auth-token")


def redact_mongo_uri(uri):
    if "://" not in uri or "@" not in uri:
        return uri

    scheme, remainder = uri.split("://", 1)
    credentials, host_part = remainder.split("@", 1)
    if ":" in credentials:
        username, _ = credentials.split(":", 1)
        credentials = f"{username}:***"
    return f"{scheme}://{credentials}@{host_part}"


try:
    client.admin.command("ping")
    users_collection.create_index("username", unique=True)
    tweets_collection.create_index([("created_at", -1)])
    tweets_collection.create_index([("author", 1), ("created_at", -1)])
except PyMongoError as db_error:
    app.logger.warning(
        "MongoDB startup check failed for %s: %s",
        redact_mongo_uri(MONGO_URI),
        db_error,
    )


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")
    response.headers["Access-Control-Allow-Origin"] = origin or "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS"
    response.headers["Vary"] = "Origin"
    return response


def api_response(data=None, message=None, status="success", http_status=200):
    payload = {"status": status}
    if message:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    return jsonify(payload), http_status


def error_response(message, http_status=400):
    return api_response(message=message, status="error", http_status=http_status)


def request_payload():
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict()


def serialize_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return str(value)


def serialize_user(user):
    return {
        "username": user.get("username"),
        "bio": user.get("bio", ""),
        "created_at": serialize_datetime(user.get("created_at")),
    }


def serialize_tweet(tweet, viewer_username=None):
    liked_by = tweet.get("liked_by", [])
    if not isinstance(liked_by, list):
        liked_by = []

    return {
        "id": str(tweet.get("_id")),
        "content": tweet.get("content", ""),
        "author": tweet.get("author", "Unknown User"),
        "created_at": serialize_datetime(tweet.get("created_at")),
        "likes": int(tweet.get("likes", 0)),
        "liked_by_current_user": bool(
            viewer_username and viewer_username in liked_by
        ),
    }


def validate_username(username):
    if not username:
        return "Username is required."
    if not USERNAME_PATTERN.fullmatch(username):
        return "Username must be 3-20 characters and use only letters, numbers, or _."
    return None


def make_token(username):
    return token_serializer.dumps({"username": username})


def username_from_token(token):
    try:
        token_data = token_serializer.loads(
            token,
            max_age=app.config["TOKEN_MAX_AGE_SECONDS"],
        )
    except (BadSignature, SignatureExpired):
        return None
    return token_data.get("username")


def bearer_token():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


def current_username():
    token = bearer_token()
    if not token:
        return None

    username = username_from_token(token)
    if not username:
        return None

    try:
        user = users_collection.find_one({"username": username}, {"username": 1})
    except PyMongoError as db_error:
        app.logger.error("Auth lookup failed: %s", db_error)
        return None

    if not user:
        return None
    return user["username"]


def require_auth():
    username = current_username()
    if not username:
        return None, error_response("Authentication required.", 401)
    return username, None


def tweet_object_id(tweet_id):
    if not tweet_id:
        return None

    try:
        return ObjectId(tweet_id)
    except (InvalidId, TypeError):
        return None


@app.route("/")
def service_root():
    return api_response(
        {
            "service": "ChirpTown API",
            "message": "Frontend is served separately. Use /api endpoints.",
        }
    )


@app.route("/api/health")
def health_check():
    try:
        client.admin.command("ping")
    except PyMongoError as db_error:
        app.logger.error("Health check failed: %s", db_error)
        return error_response("Database is unavailable.", 503)
    return api_response({"database": "connected"})


@app.route("/api/auth/signup", methods=["POST"])
def signup():
    payload = request_payload()
    username = payload.get("username", "").strip()
    password = payload.get("password", "").strip()

    username_error = validate_username(username)
    if username_error:
        return error_response(username_error)

    if len(password) < 6:
        return error_response("Password must be at least 6 characters.")

    try:
        users_collection.insert_one(
            {
                "username": username,
                "password": generate_password_hash(password),
                "bio": "",
                "created_at": datetime.now(timezone.utc),
            }
        )
        user = users_collection.find_one({"username": username})
    except DuplicateKeyError:
        return error_response("Username is already taken. Please choose another one.", 409)
    except PyMongoError as db_error:
        app.logger.error("Signup failed: %s", db_error)
        return error_response("Signup failed due to a server issue.", 500)

    return api_response(
        {
            "token": make_token(username),
            "user": serialize_user(user),
        },
        message=f"Account created. You are now posting publicly as {username}.",
        http_status=201,
    )


@app.route("/api/auth/login", methods=["POST"])
def login():
    payload = request_payload()
    username = payload.get("username", "").strip()
    password = payload.get("password", "").strip()

    if not username or not password:
        return error_response("Username and password are required.")

    try:
        user = users_collection.find_one({"username": username})
    except PyMongoError as db_error:
        app.logger.error("Login lookup failed: %s", db_error)
        return error_response("Login failed due to a server issue.", 500)

    if not user or not check_password_hash(user["password"], password):
        return error_response("Invalid username or password.", 401)

    return api_response(
        {
            "token": make_token(username),
            "user": serialize_user(user),
        },
        message=f"Welcome back, {username}.",
    )


@app.route("/api/auth/me")
def me():
    username = current_username()
    if not username:
        return api_response({"user": None})

    try:
        user = users_collection.find_one({"username": username})
    except PyMongoError as db_error:
        app.logger.error("Current user lookup failed: %s", db_error)
        return error_response("Could not load current user.", 500)

    return api_response({"user": serialize_user(user)})


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    return api_response(message="Token cleared on the client.")


@app.route("/api/tweets", methods=["GET"])
def list_tweets():
    viewer_username = current_username()

    try:
        tweets = list(
            tweets_collection.find(
                {},
                {"content": 1, "author": 1, "created_at": 1, "likes": 1, "liked_by": 1},
            )
            .sort("created_at", -1)
            .limit(100)
        )
    except PyMongoError as db_error:
        app.logger.error("Failed to load tweets: %s", db_error)
        return error_response("Could not load tweets right now.", 500)

    return api_response(
        {
            "tweets": [serialize_tweet(tweet, viewer_username) for tweet in tweets],
            "max_tweet_length": app.config["MAX_TWEET_LENGTH"],
        }
    )


@app.route("/api/tweets", methods=["POST"])
def create_tweet():
    username, auth_error = require_auth()
    if auth_error:
        return auth_error

    content = request_payload().get("content", "").strip()
    if not content:
        return error_response("Tweet cannot be empty.")
    if len(content) > app.config["MAX_TWEET_LENGTH"]:
        return error_response(
            f"Tweet is too long. Max {app.config['MAX_TWEET_LENGTH']} characters."
        )

    try:
        result = tweets_collection.insert_one(
            {
                "content": content,
                "author": username,
                "created_at": datetime.now(timezone.utc),
                "likes": 0,
                "liked_by": [],
            }
        )
        tweet = tweets_collection.find_one({"_id": result.inserted_id})
    except PyMongoError as db_error:
        app.logger.error("Failed to create tweet: %s", db_error)
        return error_response("Could not post tweet right now.", 500)

    return api_response(
        {"tweet": serialize_tweet(tweet, username)},
        message="Tweet posted.",
        http_status=201,
    )


@app.route("/api/tweets/<tweet_id>/like", methods=["POST"])
def like_tweet(tweet_id):
    username, auth_error = require_auth()
    if auth_error:
        return auth_error

    object_id = tweet_object_id(tweet_id)
    if not object_id:
        return error_response("Invalid tweet id.")

    try:
        tweet = tweets_collection.find_one_and_update(
            {"_id": object_id, "liked_by": {"$ne": username}},
            {
                "$inc": {"likes": 1},
                "$addToSet": {"liked_by": username},
            },
            return_document=ReturnDocument.AFTER,
        )
    except PyMongoError as db_error:
        app.logger.error("Failed to like tweet: %s", db_error)
        return error_response("Could not like tweet right now.", 500)

    if not tweet:
        try:
            tweet = tweets_collection.find_one({"_id": object_id})
        except PyMongoError as db_error:
            app.logger.error("Failed to verify liked tweet: %s", db_error)
            return error_response("Could not like tweet right now.", 500)

        if not tweet:
            return error_response("Tweet not found.", 404)

        return api_response(
            {"tweet": serialize_tweet(tweet, username)},
            message="You already liked this tweet.",
        )

    return api_response({"tweet": serialize_tweet(tweet, username)}, message="Like recorded.")


@app.route("/api/users/<username>", methods=["GET"])
def user_profile(username):
    username = username.strip()
    username_error = validate_username(username)
    if username_error:
        return error_response(username_error)

    viewer_username = current_username()

    try:
        user = users_collection.find_one({"username": username})
        if not user:
            return error_response("User not found.", 404)

        tweets = list(
            tweets_collection.find(
                {"author": username},
                {"content": 1, "author": 1, "created_at": 1, "likes": 1, "liked_by": 1},
            )
            .sort("created_at", -1)
            .limit(100)
        )
    except PyMongoError as db_error:
        app.logger.error("Profile lookup failed: %s", db_error)
        return error_response("Could not load profile right now.", 500)

    return api_response(
        {
            "user": serialize_user(user),
            "tweets": [serialize_tweet(tweet, viewer_username) for tweet in tweets],
        }
    )


@app.route("/api/users/bio", methods=["PUT"])
def update_bio():
    username, auth_error = require_auth()
    if auth_error:
        return auth_error

    bio = request_payload().get("bio", "").strip()
    if len(bio) > MAX_BIO_LENGTH:
        return error_response(f"Bio must be {MAX_BIO_LENGTH} characters or fewer.")

    try:
        user = users_collection.find_one_and_update(
            {"username": username},
            {"$set": {"bio": bio}},
            return_document=ReturnDocument.AFTER,
        )
    except PyMongoError as db_error:
        app.logger.error("Bio update failed: %s", db_error)
        return error_response("Could not update bio right now.", 500)

    return api_response({"user": serialize_user(user)}, message="Bio updated.")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
