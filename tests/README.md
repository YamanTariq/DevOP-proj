# ChirpTown Tests

## Backend function unit tests

These tests are fast and do not need Docker, MongoDB, Selenium, or the frontend.

```powershell
python -m pytest tests\test_backend_functions.py
```

## Selenium tests

These tests verify the Docker Compose version of ChirpTown from the browser.

## Run locally

Start the full stack first:

```powershell
docker compose up --build -d
```

Install test dependencies:

```powershell
python -m pip install -r requirements-test.txt
```

Run the suite:

```powershell
python -m pytest tests
```

The tests use `http://localhost` by default. To target another URL:

```powershell
$env:CHIRPTOWN_BASE_URL="http://localhost:8080"
python -m pytest tests
```

Screenshots are saved in `test-artifacts/`.
