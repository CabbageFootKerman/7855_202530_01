# Pinned base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy dependency list first (cache-friendly layer ordering)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Expose Flask port
EXPOSE 5000

# Production-safe startup — no debug mode
CMD ["python", "src/app.py"]