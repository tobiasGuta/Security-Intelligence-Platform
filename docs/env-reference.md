# Environment Reference
The application configuration relies on several environment variables.

- `APP_ENV`: Application environment (development/production)
- `POSTGRES_DB`: PostgreSQL database name
- `POSTGRES_USER`: PostgreSQL user
- `POSTGRES_PASSWORD`: PostgreSQL password
- `REDIS_PASSWORD`: Redis password
- `SECRET_KEY`: Backend secret key
- `SESSION_SECRET`: Backend session secret
- `API_PORT`: API service exposed port
- `WEB_PORT`: Web service exposed port
- `CORS_ALLOWED_ORIGINS`: Allowed origins for CORS
- `NEXT_PUBLIC_API_URL`: Frontend URL for communicating with API
- `NVD_API_KEY`: NVD API Key
- `SCHED_NVD_INTERVAL_HOURS`: NVD sync interval in hours
- `SCHED_KEV_INTERVAL_HOURS`: KEV sync interval in hours
- `SCHED_EPSS_CRON`: EPSS sync cron schedule
- `SCHED_ALERT_INTERVAL_MINUTES`: Alert check interval in minutes
- `SCHED_WEBHOOK_RETRY_INTERVAL_MINUTES`: Webhook retry interval in minutes
