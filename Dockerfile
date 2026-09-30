FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock .python-version README.md ./
COPY src ./src
RUN uv sync --locked --no-dev

COPY reports ./reports
ENV PATH="/app/.venv/bin:$PATH" MPLBACKEND=Agg
ENTRYPOINT ["python", "-m", "weather_edge"]
CMD ["report"]
