commands in order:
first get into venv activate (Ask ai don't ask me how)
checks passed
```
python -m py_compile app.py
node --check frontend\app.js
docker compose config
```

rebuild and test
```
docker compose down
docker compose up --build -d
```
open locally:

```
http://localhost
```

**to test persistent mongo storage:**
```
docker compose up --build -d
```

create account and post tweet. 
then stop containers
```
docker compose down
```
start again
```
docker compose up -d
```


**Selenium Testing**
checks passed:
```
python -m py_compile app.py tests\test_chirptown_ui.py
node --check frontend\app.js
docker compose config
```

to Run the selenium tests yourself:
```
docker compose up --build -d
python -m pip install -r requirements-test.txt
python -m pytest tests
```
screenshots saved in:
```
test-artifacts/
``