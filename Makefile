.DEFAULT_GOAL := help
PY := uv run python

help:            ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

setup:           ## create .venv from uv.lock and install pre-commit hooks
	uv sync
	uv run pre-commit install

lint:            ## ruff format check + lint
	uv run ruff format --check .
	uv run ruff check .

format:          ## ruff format + autofix
	uv run ruff format .
	uv run ruff check --fix .

test:            ## pytest (known-answer checks for every pipeline stage)
	uv run pytest -q

data:            ## rebuild the research data from the sources (hours; needs network)
	$(PY) -m weather_edge inventory
	$(PY) -m weather_edge prices
	$(PY) -m weather_edge trades
	$(PY) -m weather_edge truth
	$(PY) -m weather_edge forecasts --start 2025-01-01 --end 2026-09-29 --models ecmwf gfs gefs_mean gefs_spread --cycles 0 6 12 18
	$(PY) -m weather_edge labels

train:           ## fit and score the model, backtest, timing study (reads data/, writes reports/)
	$(PY) -m weather_edge checks
	$(PY) -m weather_edge model --stations KLGA --decision-hours 6 8 10 12
	$(PY) -m weather_edge model --stations EGLC KLGA KDAL RKSI CYYZ KATL KSEA SAEZ --decision-hours 12 --report reports/phase6_cities.md
	$(PY) -m weather_edge backtest --stations KLGA --decision-hours 6 12
	$(PY) -m weather_edge timing

report:          ## figures + models/metrics.json + models/emos_params.json from the committed reports
	$(PY) -m weather_edge report

notebooks:       ## execute the analysis notebooks in place (outputs are kept)
	uv run jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb

docker:          ## build the image and run the report stage inside it
	docker build -t weather-edge .
	docker run --rm -v "$$(pwd)/data:/app/data" -v "$$(pwd)/reports:/app/reports" -v "$$(pwd)/models:/app/models" weather-edge

clean:           ## remove caches and the virtual environment
	rm -rf .venv .pytest_cache .ruff_cache src/weather_edge/__pycache__ tests/__pycache__

.PHONY: help setup lint format test data train report notebooks docker clean
