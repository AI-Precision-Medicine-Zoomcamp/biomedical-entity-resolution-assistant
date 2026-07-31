# Biomedical Entity Resolution Assistant Makefile
# Centralizes all commands for setup, ingestion, execution, testing, and Docker.

.PHONY: help install download-models setup ingest index run-api run-ui test docker-up docker-down clean benchmark notebook

# Default command: display help menu
help:
	@echo "========================================================================"
	@echo "              Biomedical Entity Resolution Assistant Commands"
	@echo "========================================================================"
	@echo "Setup & Installation:"
	@echo "  make install         - Install package dependencies in editable mode"
	@echo "  make download-models - Download the scispacy en_core_sci_sm model"
	@echo "  make setup           - Run install and download-models combined"
	@echo ""
	@echo "Data Pipeline:"
	@echo "  make ingest          - Run the data ingestion pipeline (HGNC, MeSH, RxNorm)"
	@echo "  make index           - Embed and index data into Qdrant/vector database"
	@echo ""
	@echo "Execution:"
	@echo "  make run-api         - Run the FastAPI backend server (port 8000)"
	@echo "  make run-ui          - Run the Streamlit UI frontend (port 8501)"
	@echo "  make run-streamlit   - Run the Streamlit full application"
	@echo ""
	@echo "Evaluation & Benchmarking:"
	@echo "  make benchmark       - Run the automated benchmarking suite"
	@echo "  make notebook        - Launch the evaluation Jupyter notebook server"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test            - Run all unit and integration tests with pytest"
	@echo "  make clean           - Remove cache and temporary files"
	@echo ""
	@echo "Docker Management:"
	@echo "  make docker-up       - Build and start all services via docker-compose"
	@echo "  make docker-down     - Stop all Docker services"
	@echo "========================================================================"

install:
	pip install -e ".[dev]"

download-models:
	python -m pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz
	python src/embeddings/download_model.py

setup: install download-models

ingest:
	python src/ingestion/run_ingestion.py

index:
	python src/retrieval/embed_and_index.py

run-api:
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload

run-ui:
	uv run streamlit run src/app_client.py
run-streamlit:
	uv run streamlit run src/app.py

benchmark:
	uv run python benchmark.py

notebook:
	uv run jupyter notebook

test:
	pytest tests/

docker-up:
	docker-compose up --build

docker-down:
	docker-compose down

clean:
	rm -rf .pytest_cache .venv build/ dist/ *.egg-info
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.log" -delete
