.PHONY: setup run test lint clean

setup:
	python -m venv venv
	. venv/bin/activate && pip install -r requirements.txt

run:
	. venv/bin/activate && uvicorn app.main:app --reload

test:
	. venv/bin/activate && pytest tests/ -v

lint:
	. venv/bin/activate && ruff check app/ tests/

clean:
	rm -rf venv .pytest_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} +
