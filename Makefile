.PHONY: setup test run up down

setup:
	pip install -e ".[dev]"

test:
	pytest tests/

up:
	docker-compose up --build

down:
	docker-compose down
