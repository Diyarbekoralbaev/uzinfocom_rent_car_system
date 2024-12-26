# Uzinfocom Rent Car System

A comprehensive **Car Rental Management System** built with **Django** and **Django REST Framework**, providing both **Client** and **Manager** functionalities. This system supports:

1. **User Management** (Registration, Verification, Login, Role-based permissions)
2. **Vehicle Management** (CRUD, availability updates)
3. **Station Management** (CRUD, pick-up & drop-off points)
4. **Rental & Reservation Management** (rent a car, reserve in advance, manage statuses)
5. **Payments** (top-up balance, view payment history, test payment integration)
6. **SMS & Email Notifications** (SMS confirmations, email notifications)
7. **Return Car to Station** functionality with manual location validation (no external map services)

The system meets the specified requirements for role-based actions, confirmations, caching, Dockerization, testing, and more.

---

## Table of Contents
1. [Features](#features)  
2. [Project Structure](#project-structure)  
3. [Technologies Used](#technologies-used)  
4. [Installation Guide](#installation-guide)  
   - [Clone the Repository](#clone-the-repository)
   - [Environment Variables](#environment-variables)
   - [Docker Setup](#docker-setup)
   - [Manual Setup (Optional)](#manual-setup-optional)
5. [Usage](#usage)
6. [Running Tests](#running-tests)
7. [API Documentation](#api-documentation)
8. [Roles & Permissions](#roles--permissions)
9. [Core Apps Overview](#core-apps-overview)
10. [Important Endpoints](#important-endpoints)
11. [Troubleshooting & Common Commands](#troubleshooting--common-commands)
12. [License](#license)

---

## Features

**Client Capabilities**:
- **Registration** via phone/email, with OTP confirmation (SMS).
- **Balance Top-Up** (test payment flow with card details).
- **Reserve a Car** in advance (date/time range).
- **Rent a Car** immediately (date/time range).
- **Return a Car** to a station (requires physical proximity check).
- **View Payment History**, reservations, rentals, etc.

**Manager Capabilities**:
- **Create, Update, Delete** stations.
- **Create, Update, Delete** vehicles.
- **Set & Update** car prices.
- **Accept or Reject** rental & reservation requests.
- **Send SMS & Email** notifications to clients.
- **View all** payments, reservations, rentals, stations, and vehicles.

**System Requirements**:
- **Confirmation via SMS** for registration, balance top-up, and payments.
- **Confirmation via Email** upon successful action.
- **No** usage of Google/Yandex Maps for location checks; a simple Haversine-based distance check is implemented instead.
- **Transaction & Atomicity** to prevent inconsistent states when multiple users attempt to rent simultaneously.

---

## Project Structure

A simplified view:

```
.
├── common/          # Shared utilities, custom permissions
├── payments/        # PaymentModel, Payment views, tasks, tests
├── rentals/         # RentalModel, ReservationModel, logic for renting, returning
├── stations/        # StationModel, CRUD for stations
├── users/           # UserModel, Registration, Verification, Auth
├── vehicles/        # VehicleModel, Vehicle status, manager operations
├── uzinfocom_rent_car_system_drf/
│   ├── settings.py  # Main Django settings
│   ├── urls.py      # Global URL routing
│   ├── celery.py    # Celery config
│   └── wsgi.py
├── templates/       # HTML email templates
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── manage.py
└── README.md
```

---

## Technologies Used

- **Python 3.12**
- **Django 4.x** and **Django REST Framework**  
- **PostgreSQL** (relational database)  
- **Redis** (for caching & Celery broker/result backend)  
- **Celery** + **RabbitMQ or Redis** (here, Redis used as Celery broker)  
- **Swagger / drf-yasg** (API documentation)
- **Pytest / Django Test / DRF Test** (unit tests / integration tests)
- **Gunicorn** (production WSGI server)
- **Docker & docker-compose** (containerization)
- **sms.ru** or any alternative gateway (example code references a different provider, can be adjusted to sms.ru)

---

## Installation Guide

### 1. Clone the Repository
```bash
git clone https://github.com/Diyarbekoralbaev/uzinfocom_rent_car_system.git
cd uzinfocom_rent_car_system
```

### 2. Environment Variables
Create a file named `.env` in the root directory (same level as `docker-compose.yml`) with the following content (example):
```bash
SECRET_KEY="your-secret-key"
DEBUG=True
ALLOWED_HOSTS=*

DATABASE_NAME=uzinfocom_rent_car_system_db
DATABASE_USER=postgres
DATABASE_PASSWORD=02052005
DATABASE_HOST=db
DATABASE_PORT=5432

# For sms.ru or your SMS provider:
SMS_RU_API_ID="YOUR_SMS_API_ID"
ESKIZ_EMAIL=user@gmail.com
ESKIZ_PASSWORD=yourpassword

# Celery / Redis settings (if you want to override defaults):
REDIS_HOST=redis
REDIS_PORT=6379

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=user@gmail.com
EMAIL_HOST_PASSWORD=yourpassword

MAX_DISTANCE=0.5 # for location check in km
```
> **Note:** Adjust these variables according to your needs.  

### 3. Docker Setup
We have a `docker-compose.yml` and a `Dockerfile` to simplify the setup.

1. **Build and start containers**:
   ```bash
   docker-compose up -d --build
   ```
   This will spin up:
   - **web** (Django + Gunicorn or runserver)
   - **db** (PostgreSQL)
   - **redis** (for caching & Celery)
   - **celery** (background worker)

2. **Run migrations & collectstatic**:
   ```bash
   docker-compose exec web python manage.py makemigrations
   docker-compose exec web python manage.py migrate
   docker-compose exec web python manage.py collectstatic --noinput
   ```
   > **Note**: `collectstatic` is only needed if you serve static files in production.

3. **(Optional) Create a superuser**:
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

4. **Check logs**:
   ```bash
   docker-compose logs -f
   ```

The app will be available at `http://localhost:8000/` by default.

### 4. Manual Setup (Optional)

If you prefer to run locally without Docker:
1. Create and activate a **virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. Make sure **PostgreSQL** and **Redis** are running. Update `DATABASES` and `CACHES` in `settings.py` (or via environment variables).
4. Run migrations and start the server:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

---

## Usage

- **Login/Registration** endpoints are under `/users/...`  
- **Stations** endpoints are under `/stations/...`  
- **Vehicles** endpoints are under `/vehicles/...`  
- **Rentals & Reservations** endpoints under `/rentals/...`  
- **Payments** endpoints under `/payments/...`  

All major endpoints are secured by JWT authentication. Obtain your tokens via the `/users/login/` endpoint.

---

## Running Tests

We have extensive test coverage using Django’s built-in `TestCase` and DRF’s `APITestCase`.

- **Via Docker**:
  ```bash
  docker-compose exec web python manage.py test
  ```
- **Locally** (if not using Docker):
  ```bash
  python manage.py test
  ```

You’ll see output for all apps: **users**, **payments**, **rentals**, **stations**, **vehicles**, etc.

---

## API Documentation

Swagger UI is enabled. Once the server is running, visit:

```
http://localhost:8000/swagger/
```
You can also access JSON or YAML schemas at:
```
http://localhost:8000/swagger.json
http://localhost:8000/swagger.yaml
```

This covers all REST endpoints with schema details, request/response bodies, and example requests.

---

## Roles & Permissions

- **Client (CL)**  
  - Can register, top-up balance, rent, reserve, return a car, view only their own data (e.g., rentals, payments).
  - **Cannot** create/delete stations or vehicles.

- **Manager (MN)**  
  - Full access to CRUD stations/vehicles.
  - Can accept/reject rentals/reservations.
  - Can view **all** payments, rentals, reservations.
  - Can set status for vehicles, rentals, and reservations.
  - Has permission to send messages to clients.

Role-based logic is enforced in each app’s `permission_classes` (e.g., `IsManager`, `IsClient`, or custom checks).

---

## Core Apps Overview

1. **`users/`**  
   - `UserModel` (extends `AbstractUser`)
   - Registration, OTP verification, login, password reset
   - Role-based authentication
   - Tests & endpoints for user management

2. **`vehicles/`**  
   - `VehicleModel` with `VehicleStatusChoices` (AVAILABLE, RENTED, MAINTENANCE)
   - Create, update, delete by managers
   - List only available vehicles for clients

3. **`stations/`**  
   - `StationModel` (name, lat, lon, active/inactive)
   - Manager can activate/deactivate

4. **`rentals/`**  
   - `RentalModel`, `ReservationModel`
   - Rent a car or reserve for future
   - Status transitions: PENDING -> ACTIVE -> COMPLETED or CANCELLED
   - Return car to station verifying user’s geolocation

5. **`payments/`**  
   - `PaymentModel` for client’s balance top-up
   - Payment test flow (card number, expiry, CVV)
   - Celery task to send email receipt

6. **`common/`**  
   - Shared logic, custom permission classes (`permissions.py`)

---

## Important Endpoints

1. **User Registration & Verification**  
   - `POST /users/register/`  
   - `POST /users/verify/`  
   - `POST /users/login/`  

2. **Users**  
   - `GET /users/me/` (view profile)  
   - `POST /users/change-password/`  

3. **Stations**  
   - `GET /stations/` (list stations; managers see all, clients see only active)  
   - `POST /stations/` (create station, manager only)  

4. **Vehicles**  
   - `GET /vehicles/` (list vehicles; clients see only available)  
   - `POST /vehicles/` (create, manager only)  
   - `POST /vehicles/{id}/set-status/` (manager only)

5. **Rentals & Reservations**  
   - `POST /rentals/` (create rental)  
   - `POST /rentals/{id}/set-status/` (manager sets status)  
   - `POST /rentals/return-car-to-station/` (client returns car)  
   - `POST /rentals/reservations/` (client reserves)  
   - `POST /rentals/reservations/{id}/set-status/` (manager confirms/cancels)

6. **Payments**  
   - `POST /payments/` (create a new payment, top-up)  
   - `GET /payments/` (list payments; client sees own, manager sees all)

---

## Troubleshooting & Common Commands

- **Start services**:
  ```bash
  docker-compose up -d
  ```
- **Stop services**:
  ```bash
  docker-compose down
  ```
- **Rebuild images**:
  ```bash
  docker-compose up -d --build
  ```
- **Check logs**:
  ```bash
  docker-compose logs -f
  ```
- **Run migrations**:
  ```bash
  docker-compose exec web python manage.py migrate
  ```

If you face database connection issues, ensure the container **db** is healthy and your environment variables are set correctly. 

---