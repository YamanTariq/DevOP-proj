const API_BASE =
    window.CHIRPTOWN_API_BASE ||
    (window.location.protocol === "file:" ? "http://127.0.0.1:5000" : "");
const TOKEN_KEY = "chirptown_token";

const state = {
    user: null,
    maxTweetLength: 280,
};

const page = document.body.dataset.page;

function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
    if (token) {
        localStorage.setItem(TOKEN_KEY, token);
    } else {
        localStorage.removeItem(TOKEN_KEY);
    }
}

async function apiRequest(path, options = {}) {
    const headers = {
        Accept: "application/json",
        ...(options.headers || {}),
    };

    if (options.body) {
        headers["Content-Type"] = "application/json";
    }

    const token = getToken();
    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${path}`, {
        method: options.method || "GET",
        headers,
        body: options.body ? JSON.stringify(options.body) : undefined,
    });

    const payload = await response.json().catch(() => ({
        status: "error",
        message: "Server returned an invalid response.",
    }));

    if (!response.ok || payload.status === "error") {
        throw new Error(payload.message || "Request failed.");
    }

    return payload;
}

function showAlert(message, type = "success") {
    const alerts = document.querySelector("[data-alerts]");
    if (!alerts || !message) {
        return;
    }

    alerts.innerHTML = "";
    const alert = document.createElement("article");
    alert.className = `alert ${type}`;
    alert.textContent = message;
    alerts.appendChild(alert);
}

function clearAlerts() {
    const alerts = document.querySelector("[data-alerts]");
    if (alerts) {
        alerts.innerHTML = "";
    }
}

function formatDate(value) {
    if (!value) {
        return "Just now";
    }

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleString(undefined, {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
    });
}

function profileUrl(username) {
    return `profile.html?username=${encodeURIComponent(username)}`;
}

function renderAuthState() {
    document.querySelectorAll("[data-auth-required]").forEach((element) => {
        element.hidden = !state.user;
    });

    document.querySelectorAll("[data-guest-only]").forEach((element) => {
        element.hidden = Boolean(state.user);
    });

    document.querySelectorAll("[data-current-username]").forEach((element) => {
        element.textContent = state.user ? state.user.username : "";
    });

    document.querySelectorAll("[data-profile-link]").forEach((element) => {
        if (state.user) {
            element.href = profileUrl(state.user.username);
        }
    });
}

async function loadCurrentUser() {
    if (!getToken()) {
        state.user = null;
        renderAuthState();
        return;
    }

    try {
        const payload = await apiRequest("/api/auth/me");
        state.user = payload.data.user;
        if (!state.user) {
            setToken(null);
        }
    } catch (error) {
        setToken(null);
        state.user = null;
    }

    renderAuthState();
}

function setupLogout() {
    document.querySelectorAll("[data-logout]").forEach((button) => {
        button.addEventListener("click", async () => {
            try {
                await apiRequest("/api/auth/logout", { method: "POST" });
            } catch (error) {
                // Stateless logout still completes locally even if the API is unavailable.
            }
            setToken(null);
            state.user = null;
            window.location.href = "index.html";
        });
    });
}

function createTweetCard(tweet) {
    const card = document.createElement("article");
    card.className = "tweet-card";
    card.dataset.tweetId = tweet.id;

    const header = document.createElement("header");

    const author = document.createElement("a");
    author.className = "tweet-author";
    author.href = profileUrl(tweet.author);
    author.textContent = `@${tweet.author || "unknown"}`;

    const time = document.createElement("time");
    time.className = "tweet-time";
    time.dateTime = tweet.created_at || "";
    time.textContent = formatDate(tweet.created_at);

    header.append(author, time);

    const content = document.createElement("p");
    content.textContent = tweet.content || "";

    const footer = document.createElement("footer");
    footer.className = "tweet-footer";

    const likes = document.createElement("span");
    likes.className = "meta";
    likes.textContent = `${tweet.likes || 0} likes`;

    const likeButton = document.createElement("button");
    likeButton.type = "button";
    likeButton.className = "like-button";
    likeButton.textContent = tweet.liked_by_current_user
        ? "Liked"
        : state.user
          ? "Like"
          : "Login to like";
    likeButton.disabled = Boolean(tweet.liked_by_current_user);
    likeButton.addEventListener("click", async () => {
        if (!state.user) {
            showAlert("Please login to like posts.", "error");
            return;
        }

        likeButton.disabled = true;
        try {
            const payload = await apiRequest(`/api/tweets/${tweet.id}/like`, { method: "POST" });
            const updatedTweet = payload.data.tweet;
            tweet.liked_by_current_user = Boolean(updatedTweet.liked_by_current_user);
            likes.textContent = `${updatedTweet.likes} likes`;
            likeButton.textContent = tweet.liked_by_current_user ? "Liked" : "Like";
            if (payload.message) {
                showAlert(payload.message);
            }
        } catch (error) {
            showAlert(error.message, "error");
        } finally {
            likeButton.disabled = Boolean(tweet.liked_by_current_user);
        }
    });

    footer.append(likes, likeButton);
    card.append(header, content, footer);
    return card;
}

function renderTweets(container, tweets) {
    container.innerHTML = "";

    if (!tweets.length) {
        const empty = document.createElement("article");
        empty.className = "empty-state";
        empty.textContent = "No posts yet. Be the first voice in the feed.";
        container.appendChild(empty);
        return;
    }

    tweets.forEach((tweet) => container.appendChild(createTweetCard(tweet)));
}

function updateFeedCount(count) {
    const counter = document.querySelector("[data-feed-count]");
    if (counter) {
        counter.textContent = count === 1 ? "1 post" : `${count} posts`;
    }
}

async function loadFeed() {
    const container = document.querySelector("[data-tweet-list]");
    if (!container) {
        return;
    }

    try {
        const payload = await apiRequest("/api/tweets");
        const tweets = payload.data.tweets || [];
        state.maxTweetLength = payload.data.max_tweet_length || 280;
        renderTweets(container, tweets);
        updateFeedCount(tweets.length);
        setupTweetCounter();
    } catch (error) {
        container.innerHTML = "";
        const empty = document.createElement("article");
        empty.className = "empty-state";
        empty.textContent = "Could not load posts right now.";
        container.appendChild(empty);
        showAlert(error.message, "error");
    }
}

function setupTweetCounter() {
    const textarea = document.querySelector("#tweet-content");
    const counter = document.querySelector("[data-char-counter]");
    if (!textarea || !counter) {
        return;
    }

    textarea.maxLength = state.maxTweetLength;
    const updateCounter = () => {
        counter.textContent = `${state.maxTweetLength - textarea.value.length} chars left`;
    };

    textarea.addEventListener("input", updateCounter);
    updateCounter();
}

function setupTweetForm() {
    const form = document.querySelector("[data-tweet-form]");
    if (!form) {
        return;
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        clearAlerts();

        const button = form.querySelector("button[type='submit']");
        const content = form.elements.content.value.trim();
        button.disabled = true;

        try {
            const payload = await apiRequest("/api/tweets", {
                method: "POST",
                body: { content },
            });
            form.reset();
            setupTweetCounter();
            showAlert(payload.message || "Tweet posted.");
            await loadFeed();
        } catch (error) {
            showAlert(error.message, "error");
        } finally {
            button.disabled = false;
        }
    });
}

function setupAuthForm() {
    const form = document.querySelector("[data-auth-form]");
    if (!form) {
        return;
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        clearAlerts();

        const mode = form.dataset.authForm;
        const button = form.querySelector("button[type='submit']");
        button.disabled = true;

        try {
            const payload = await apiRequest(`/api/auth/${mode}`, {
                method: "POST",
                body: {
                    username: form.elements.username.value.trim(),
                    password: form.elements.password.value,
                },
            });
            setToken(payload.data.token);
            state.user = payload.data.user;
            showAlert(payload.message || "Signed in.");
            window.location.href = "index.html";
        } catch (error) {
            showAlert(error.message, "error");
        } finally {
            button.disabled = false;
        }
    });
}

function setupBioCounter() {
    const textarea = document.querySelector("#bio");
    const counter = document.querySelector("[data-bio-counter]");
    if (!textarea || !counter) {
        return;
    }

    const updateCounter = () => {
        counter.textContent = `${textarea.maxLength - textarea.value.length} chars left`;
    };

    textarea.addEventListener("input", updateCounter);
    updateCounter();
}

async function loadProfile() {
    const usernameFromUrl = new URLSearchParams(window.location.search).get("username");
    const username = usernameFromUrl || (state.user && state.user.username);

    if (!username) {
        showAlert("Login or open a profile from the feed.", "error");
        return;
    }

    try {
        const payload = await apiRequest(`/api/users/${encodeURIComponent(username)}`);
        const profile = payload.data.user;
        const tweets = payload.data.tweets || [];
        const isOwner = state.user && state.user.username === profile.username;

        document.title = `${profile.username} - ChirpTown`;
        document.querySelector("[data-profile-username]").textContent = `@${profile.username}`;
        document.querySelector("[data-profile-meta]").textContent = profile.created_at
            ? `Joined ${formatDate(profile.created_at)}`
            : "";
        document.querySelector("[data-profile-bio]").textContent =
            profile.bio || "No bio yet.";

        const bioForm = document.querySelector("[data-bio-form]");
        if (bioForm) {
            bioForm.hidden = !isOwner;
            bioForm.elements.bio.value = profile.bio || "";
            setupBioCounter();
        }

        const container = document.querySelector("[data-profile-tweets]");
        renderTweets(container, tweets);
        updateFeedCount(tweets.length);
    } catch (error) {
        showAlert(error.message, "error");
    }
}

function setupBioForm() {
    const form = document.querySelector("[data-bio-form]");
    if (!form) {
        return;
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        clearAlerts();

        const button = form.querySelector("button[type='submit']");
        button.disabled = true;

        try {
            const payload = await apiRequest("/api/users/bio", {
                method: "PUT",
                body: { bio: form.elements.bio.value },
            });
            state.user = payload.data.user;
            showAlert(payload.message || "Bio updated.");
            await loadProfile();
        } catch (error) {
            showAlert(error.message, "error");
        } finally {
            button.disabled = false;
        }
    });
}

async function boot() {
    setupLogout();
    setupAuthForm();
    setupTweetForm();
    setupBioForm();

    await loadCurrentUser();

    if (page === "feed") {
        await loadFeed();
    }

    if (page === "profile") {
        await loadProfile();
    }
}

boot();
