FROM python:3.11-slim

# ecCodes, which decodes the GRIB forecast files, ships as the eccodeslib wheel, so the slim image
# needs no system packages. uv pins the rest from the lock file.
RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --locked --no-dev

COPY reports ./reports
COPY models ./models

# the report stage needs only the committed reports; the data stages need data/ mounted
CMD ["uv", "run", "python", "-m", "weather_edge", "report"]
