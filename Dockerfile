# Dockerfile
FROM python:3.12-slim

# Prevents Python from writing .pyc files and buffers stdout (so logs show up immediately)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (separate layer — only rebuilds if requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the bot code
COPY . .

# Run as non-root user for a bit of security hygiene
RUN useradd --create-home botuser
USER botuser

CMD ["python", "main.py"]
