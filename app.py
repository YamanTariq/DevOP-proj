from datetime import datetime, timezone
import os
import re

from flask import Flask, flash, redirect, render_template, request, session, url_for
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "devops_secret_key")
app.config["MAX_TWEET_LENGTH"] = 280


def running_in_docker():
    return os.path.exists("/.dockerenv")


# MongoDB Connection
default_mongo_host = "host.docker.internal" if running_in_docker() else "localhost"
MONGO_URI = os.getenv("MONGO_URI", f"mongodb://{default_mongo_host}:27017")
client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    socketTimeoutMS=10000,
)
db = client.microblog_db
tweets_collection = db.tweets
users_collection = db.users
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")

try:
    client.admin.command("ping")
    users_collection.create_index("username", unique=True)
except PyMongoError as db_error:
    app.logger.warning("MongoDB startup check failed for %s: %s", MONGO_URI, db_error)


def current_user():
    return session.get("user")


def validate_username(username):
    if not username:
        return "Username is required."
    if not USERNAME_PATTERN.fullmatch(username):
        return "Username must be 3-20 characters and use only letters, numbers, or _."
    return None


@app.template_filter("format_datetime")
def format_datetime(value):
    if not value:
        return "Just now"
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone().strftime("%d %b %Y, %I:%M %p")
    return str(value)

@app.route('/')
def index():
    try:
        all_tweets = list(
            tweets_collection.find({}, {"content": 1, "author": 1, "created_at": 1})
            .sort("_id", -1)
            .limit(100)
        )
    except PyMongoError as db_error:
        app.logger.error("Failed to load tweets: %s", db_error)
        flash("Could not load tweets right now. Please try again.", "error")
        all_tweets = []

    return render_template(
        'index.html',
        tweets=all_tweets,
        current_user=current_user(),
        max_tweet_length=app.config["MAX_TWEET_LENGTH"],
    )

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user():
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        username_error = validate_username(username)
        if username_error:
            flash(username_error, "error")
            return render_template('signup.html', form_username=username)

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template('signup.html', form_username=username)

        try:
            hashed_pw = generate_password_hash(password)
            users_collection.insert_one(
                {
                    "username": username,
                    "password": hashed_pw,
                    "created_at": datetime.now(timezone.utc),
                }
            )
        except DuplicateKeyError:
            flash("Username is already taken. Please choose another one.", "error")
            return render_template('signup.html', form_username=username)
        except PyMongoError as db_error:
            app.logger.error("Signup failed: %s", db_error)
            flash("Signup failed due to a server issue. Please try again.", "error")
            return render_template('signup.html', form_username=username)

        session['user'] = username
        flash(f"Account created. You are now posting publicly as {username}.", "success")
        return redirect(url_for('index'))

    return render_template('signup.html', form_username='')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user():
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template('login.html', form_username=username)

        try:
            user = users_collection.find_one({"username": username})
        except PyMongoError as db_error:
            app.logger.error("Login lookup failed: %s", db_error)
            flash("Login failed due to a server issue. Please try again.", "error")
            return render_template('login.html', form_username=username)

        if not user or not check_password_hash(user['password'], password):
            flash("Invalid username or password.", "error")
            return render_template('login.html', form_username=username)

        session['user'] = username
        flash(f"Welcome back, {username}.", "success")
        return redirect(url_for('index'))

    return render_template('login.html', form_username='')

@app.route('/post', methods=['POST'])
def post_tweet():
    user = current_user()
    if not user:
        flash("Please login to post a tweet.", "error")
        return redirect(url_for('login'))

    content = request.form.get('content', '').strip()
    if not content:
        flash("Tweet cannot be empty.", "error")
        return redirect(url_for('index'))

    if len(content) > app.config["MAX_TWEET_LENGTH"]:
        flash(
            f"Tweet is too long. Max {app.config['MAX_TWEET_LENGTH']} characters.",
            "error",
        )
        return redirect(url_for('index'))

    try:
        tweets_collection.insert_one(
            {
                "content": content,
                "author": user,
                "created_at": datetime.now(timezone.utc),
            }
        )
        flash("Tweet posted.", "success")
    except PyMongoError as db_error:
        app.logger.error("Failed to create tweet: %s", db_error)
        flash("Could not post tweet right now. Please try again.", "error")

    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    if current_user():
        session.pop('user', None)
        flash("You have been logged out.", "success")
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)