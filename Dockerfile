FROM python:3.12-slim

WORKDIR /workspace

# Install system deps (optional, for pandas/numpy)
RUN apt-get update && apt-get install -y build-essential
RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv pip install --system --no-cache .


CMD ["sleep", "infinity"]
