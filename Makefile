.PHONY: setup lint format test data train report notebooks docker clean

setup:
	uv sync --locked

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .

test:
	uv run pytest -v

# hours, and 36 GB of fills streamed from Hugging Face
data:
	uv run python -m weather_edge inventory
	uv run python -m weather_edge prices
	uv run python -m weather_edge trades
	uv run python -m weather_edge truth
	uv run python -m weather_edge forecasts --start 2025-01-01 --end 2026-09-29 --models ecmwf gfs gefs_mean gefs_spread --cycles 0 6 12 18
	uv run python -m weather_edge forecasts --start 2025-01-01 --end 2026-09-29 --models nbm_tmax nbm_tmax_spread --cycles 0 6 12 18
	uv run python -m weather_edge labels

# the model in eight cities, the NYC decision-hour sweep, the backtest and the timing study
train:
	uv run python -m weather_edge checks
	uv run python -m weather_edge model --stations EGLC KLGA KDAL RKSI CYYZ KATL KSEA SAEZ --decision-hours 12 --report reports/phase6_cities.md
	uv run python -m weather_edge model --stations KLGA --decision-hours 6 8 10 12
	uv run python -m weather_edge backtest --stations KLGA EGLC --decision-hours 6 12
	uv run python -m weather_edge timing

# figures, models/metrics.json and the EMOS parameter snapshot, from the committed reports
report:
	uv run python -m weather_edge report

notebooks:
	uv run jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb

docker:
	docker build -t weather-edge .
	docker run --rm -v "$$(pwd)/reports:/app/reports" -v "$$(pwd)/models:/app/models" weather-edge

clean:
	rm -rf .venv .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
