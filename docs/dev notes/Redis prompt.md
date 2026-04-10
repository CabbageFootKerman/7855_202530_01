# Future Containerization Prompt: Flask + Redis

## Goal
Enable simple, portable deployment of the Flask app with Redis for rate limiting, using containerization best practices.

## Requirements
- Each service (Flask app, Redis) should run in its own container.
- Use Docker Compose to orchestrate both containers together.
- The Flask app should connect to Redis using the service name (not localhost).

## Example Docker Compose Setup

```yaml

version: '3.8'
services:
	redis:
	image: redis:latest
	container_name: redis-limiter
	ports:
	- "6379:6379"
	flask:
	build: .
	container_name: flask-app
	environment:
	- RATELIMIT_STORAGE_URL=redis://redis:6379
	ports:
	- "5000:5000"
	depends_on:
	- redis
```

## Flask App Configuration
- In your Flask config, set:
  ```python
  RATELIMIT_STORAGE_URL = "redis://redis:6379"
  ```
  (Note: Use the service name `redis` as the hostname, not `localhost`.)

## Workflow
1. Build and start both containers:
   ```
   docker-compose up --build
   ```
2. Both Flask and Redis will run and communicate on the same Docker network.
3. To stop:
   ```
   docker-compose down
   ```

## Notes

- Do not run Redis inside the Flask app container. Each service should have its own container.

- This setup is portable and works on any system with Docker and Docker Compose.

- **Production Security:**
	- By default, Redis is open to all network interfaces and has no password. This is insecure for production.
	- Always bind Redis to localhost or a private network. In Docker Compose, omit the `ports:` section or use `127.0.0.1:6379:6379` to restrict access.
	- Set a Redis password using the `requirepass` directive (see Redis docs) and provide it in your Flask config/environment.
	- Never expose Redis to the public internet.

- For production, consider securing Redis and using environment variables for secrets.
