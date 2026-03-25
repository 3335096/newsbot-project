# NewsBot Project

This project is a NewsBot application with a FastAPI backend and a Telegram bot frontend.

## Project Structure

- `app/`: FastAPI application, API routes, services, scheduler.
- `bot/`: Telegram bot using aiogram.
- `core/`: Common configuration and utilities.
- `docker/`: Dockerfiles for API and bot services.
- `scripts/`: Helper scripts.
- Root directory: Configuration files, docker-compose, README, environment variables.

## Setup and Installation

1. Copy environment file and set values:
   - `cp .env.example .env`
2. Start services:
   - `docker compose up --build`

## Database

- Alembic migrations are stored in `migrations/`.
- Initial schema migration:
  - `alembic upgrade head`
- Fallback initializer:
  - `python scripts/init_db.py`

## Iteration 1 scope

- Project skeleton (FastAPI + aiogram + Docker compose).
- Core DB models and initial migration based on technical specification.
- Basic bot authorization using whitelist/admin lists.
- Basic API routes:
  - `GET /health`
  - `GET /api/drafts`
  - `POST /api/drafts/{id}/approve`
  - `POST /api/drafts/{id}/reject`
  - `POST /bot/webhook` (placeholder)
