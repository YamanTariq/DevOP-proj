import os
import time
import uuid
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


BASE_URL = os.getenv("CHIRPTOWN_BASE_URL", "http://localhost").rstrip("/")
ARTIFACT_DIR = Path(os.getenv("CHIRPTOWN_TEST_ARTIFACTS", "test-artifacts"))
DEFAULT_PASSWORD = "TestPass123"


def wait_for_application(base_url):
    deadline = time.time() + 30
    health_url = f"{base_url}/api/health"

    while time.time() < deadline:
        try:
            with urlopen(health_url, timeout=2) as response:
                if response.status == 200:
                    return
        except URLError:
            time.sleep(1)

    pytest.fail(f"Application did not become ready at {health_url}")


@pytest.fixture(scope="session")
def base_url():
    wait_for_application(BASE_URL)
    return BASE_URL


@pytest.fixture
def driver():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1000")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    browser = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    browser.implicitly_wait(1)

    yield browser

    browser.quit()


def screenshot(driver, name):
    driver.save_screenshot(str(ARTIFACT_DIR / f"{name}.png"))


def wait(driver):
    return WebDriverWait(driver, 12)


def unique_username():
    return f"ui_{uuid.uuid4().hex[:10]}"


def signup_user(driver, base_url, username=None, password=DEFAULT_PASSWORD):
    username = username or unique_username()
    driver.get(f"{base_url}/signup.html")

    driver.find_element(By.ID, "username").send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "[data-auth-form='signup'] button").click()

    wait(driver).until(EC.url_contains("index.html"))
    wait(driver).until(
        EC.text_to_be_present_in_element((By.CSS_SELECTOR, "[data-current-username]"), username)
    )
    return username, password


def post_tweet(driver, content):
    textarea = wait(driver).until(EC.visibility_of_element_located((By.ID, "tweet-content")))
    textarea.clear()
    textarea.send_keys(content)
    driver.find_element(By.CSS_SELECTOR, "[data-tweet-form] button").click()
    tweet_locator = (
        By.XPATH,
        f"//article[contains(@class, 'tweet-card')][contains(., {content!r})]",
    )
    return wait(driver).until(EC.visibility_of_element_located(tweet_locator))


def test_homepage_loads_feed_header(driver, base_url):
    driver.get(base_url)

    wait(driver).until(
        EC.text_to_be_present_in_element((By.CSS_SELECTOR, ".brand strong"), "ChirpTown")
    )
    wait(driver).until(
        EC.text_to_be_present_in_element((By.CSS_SELECTOR, ".feed-header h2"), "Latest Posts")
    )

    assert "Microblog feed" in driver.page_source
    screenshot(driver, "01-homepage-loads")


def test_signup_logout_and_login_flow(driver, base_url):
    username, password = signup_user(driver, base_url)
    screenshot(driver, "02-after-signup")

    driver.find_element(By.CSS_SELECTOR, "[data-logout]").click()
    wait(driver).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-guest-only]")))

    driver.get(f"{base_url}/login.html")
    driver.find_element(By.ID, "username").send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "[data-auth-form='login'] button").click()

    wait(driver).until(EC.url_contains("index.html"))
    wait(driver).until(
        EC.text_to_be_present_in_element((By.CSS_SELECTOR, "[data-current-username]"), username)
    )
    screenshot(driver, "03-after-login")


def test_authenticated_user_can_post_tweet(driver, base_url):
    signup_user(driver, base_url)
    content = f"Selenium post {uuid.uuid4().hex}"

    tweet = post_tweet(driver, content)

    assert content in tweet.text
    screenshot(driver, "04-post-created")


def test_user_can_like_same_tweet_only_once(driver, base_url):
    signup_user(driver, base_url)
    content = f"Like once {uuid.uuid4().hex}"
    tweet = post_tweet(driver, content)

    like_button = tweet.find_element(By.CSS_SELECTOR, ".like-button")
    like_button.click()

    wait(driver).until(
        EC.text_to_be_present_in_element(
            (By.CSS_SELECTOR, f"[data-tweet-id='{tweet.get_attribute('data-tweet-id')}'] .meta"),
            "1 likes",
        )
    )
    wait(driver).until(
        EC.text_to_be_present_in_element(
            (By.CSS_SELECTOR, f"[data-tweet-id='{tweet.get_attribute('data-tweet-id')}'] .like-button"),
            "Liked",
        )
    )

    driver.execute_script(
        "const button = arguments[0]; button.disabled = false; button.click();",
        like_button,
    )
    wait(driver).until(
        EC.text_to_be_present_in_element(
            (By.CSS_SELECTOR, "[data-alerts]"),
            "You already liked this tweet.",
        )
    )

    updated_tweet = driver.find_element(
        By.CSS_SELECTOR,
        f"[data-tweet-id='{tweet.get_attribute('data-tweet-id')}']",
    )
    assert "1 likes" in updated_tweet.text
    assert "Liked" in updated_tweet.text
    screenshot(driver, "05-like-once")
