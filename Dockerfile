FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and uv.lock to install dependencies first (cached layer)
COPY pyproject.toml uv.lock ./

# Synchronize dependencies
RUN uv sync --frozen --no-cache

# Copy project source code
COPY . .

# Expose port 8000
EXPOSE 8000

# Start server
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
