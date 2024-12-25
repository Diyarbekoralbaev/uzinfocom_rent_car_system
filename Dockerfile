# Use an official Python runtime as the base image
FROM python:3.12-slim-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install the project dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir psycopg[pool] gunicorn

# Copy the project code into the container
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "uzinfocom_rent_car_system_drf.wsgi:application"]
