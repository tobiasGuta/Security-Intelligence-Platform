# Security Intelligence Platform

A self-hosted cybersecurity vulnerability intelligence platform.

## Quick Start
1. Clone and configure environment: `cp .env.example .env`
2. Start services: `docker compose up -d`
3. Run migrations: `make migrate`
4. Create admin user: `make create-admin`
5. Access UI at http://localhost:3000

## Architecture
- **API**: FastAPI backend
- **Web**: Next.js frontend
- **Worker**: Worker task processor
- **Scheduler**: Scheduled task runner
- **Postgres**: Primary database
- **Redis**: Cache & Message Broker

## Development
Use provided make targets for common tasks.

## Make targets
Run `make help` to see all available targets.
