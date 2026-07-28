install:
	python -m pip install -r requirements-dev.txt

lint:
	python -m ruff check .

test:
	python -m pytest -q

demo:
	python scripts/run_synthetic_demo.py

check:
	python -m ruff check .
	python -m pytest -q
