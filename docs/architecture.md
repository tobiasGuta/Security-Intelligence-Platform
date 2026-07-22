# Architecture Overview
The platform is designed as a modular monorepo containing 6 services:
- **api**: FastAPI backend
- **web**: Next.js frontend
- **worker**: Task worker for asynchronous operations
- **scheduler**: Scheduling service for periodic tasks
- **postgres**: Primary database (PostgreSQL 17)
- **redis**: Cache and Message Broker (Redis 7)
