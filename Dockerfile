# Use the official Python image as a base
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app 

# Set the working directory
WORKDIR /app

# Install system dependencies, including git, PostgreSQL dev libraries, and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libpq-dev \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY . /app/


EXPOSE 7050


# Command to run the FastAPI app
CMD ["uvicorn", "custom_agent_builder.api:app", "--host", "0.0.0.0", "--port", "7050"]
