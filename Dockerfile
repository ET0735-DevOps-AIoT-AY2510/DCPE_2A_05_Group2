# Step 1: Base Image
FROM python:3.11-slim

# Step 2: Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Step 3: Set working directory
WORKDIR /app

# Step 4: Copy all files (includes run_website.py and website/)
COPY . /app

# Step 5: Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Step 6: Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Step 7: Copy entrypoint script
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Step 8: Expose Flask port
EXPOSE 5000

# Step 9: Use entrypoint for seeding + starting app
ENTRYPOINT ["./docker-entrypoint.sh"]
