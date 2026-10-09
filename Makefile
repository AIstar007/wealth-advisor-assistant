install:
	python -m pip install -r requirements.txt

test:
	pytest -q

lint:
	ruff check app tests
	ruff format --check app tests

run:
	uvicorn app.main:app --reload

run-azure:
	uvicorn app.main:app --reload

run-foundry:
	RUN_MODE=foundry uvicorn app.main:app --reload

doctor:
	python -m app.doctor

doctor-live:
	python -m app.doctor --live

demo-offline:
	python -m app.demo_offline
