# Use the official Python image as a base
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the shared requirements file into the container
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY . /app/

# Expose the Streamlit app port
EXPOSE 8501

# Command to run the Streamlit app
CMD ["streamlit", "run", "custom_agent_builder.app:app", "--server.baseUrlPath=agent-chat", "--server.port=8501", "--server.address=0.0.0.0"]
