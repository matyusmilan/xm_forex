# Summary
A RESTful API to simulate a Forex trading platform with WebSocket support for real-time order updates.
# Required
```commandline
python --version
Python 3.11.0rc1

poetry --version
Poetry (version 1.8.3)

docker --version
Docker version 24.0.7, build 24.0.7-0ubuntu2~22.04.1

git --version
git version 2.34.1
```
# Usage
1.) Get the source
```commandline
git clone https://github.com/matyusmilan/xm_forex.git
```
## Localhost
1.) Start API
```commandline
cd xm_forex/demo-app
python3.12 -m venv env
source env/bin/activate
poetry install
uvicorn demo_app.main:app --reload --workers 1 --host 0.0.0.0 --port 8080
```
2.) Visit http://127.0.0.1:8080/docs in your favourite browser
## Docker
1.) Build service
```commandline
cd xm_forex/demo-app
docker build -t demo_app:service --target service .
```
2.) Start service
```commandline
docker run -it -p 8080:8000 demo_app:service
```
3.) Visit http://127.0.0.1:8080/docs in your favourite browser

# Testing

## Local
1.) Get the source
```commandline
git clone https://github.com/matyusmilan/xm_forex.git
cd xm_forex/demo-app
pytest --html=tests/reports/report.html --cov=demo_app tests/ -v
```
2.) You can see the test result and coverage in console log

3.) Open the demo-app/tests/reports/report.html page in the browser for the test report.

## Docker
```commandline
git clone https://github.com/matyusmilan/xm_forex.git
cd xm_forex/demo-app
docker build -t demo_app:test --target test .
```
### Linters
```commandline
docker run -it demo_app:test flake8 --max-line-length 120 .
docker run -it demo_app:test black . --check
docker run -it demo_app:test isort . --check-only --profile black
docker run -it demo_app:test bandit .
docker run -it demo_app:test ruff check .
docker run -it demo_app:test safety check 
```

### Integration + e2e
```commandline
docker run -it demo_app:test pytest --html=tests/reports/report.html --cov=demo_app tests/ -v
```

### Performance
```commandline
docker run --network="host" -it demo_app:test python tests/performance/test_websocket.py
```
# Technology

## API
- FastAPI - https://fastapi.tiangolo.com/
- SXLModel - https://sqlmodel.tiangolo.com/

## Testing
- pytest - https://docs.pytest.org/

## Environment
- Poetry - https://python-poetry.org/
- Docker - https://www.docker.com/

