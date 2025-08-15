# BilgiislemTool

## Environment Variables

The application initializes an administrator account using credentials supplied via environment variables and uses a secret key for session handling.

- `ADMIN_USERNAME` – Username for the initial administrator.
- `ADMIN_PASSWORD` – Password for the initial administrator.
- `SESSION_SECRET` – Secret key used to sign session cookies. If omitted, the application will generate a random value at startup and sessions will reset when the server restarts.

The admin credentials are optional; if not provided, no default admin user is created. Defining `SESSION_SECRET` is recommended for stable sessions, but the server will still start even if it is missing.

When using Docker Compose, provide any desired variables in your environment or an `.env` file:

```
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_admin_password
SESSION_SECRET=some_long_random_string
```

## Authentication

Administrative pages now require users to be authenticated. Visit `/login` to sign in and `/logout` to terminate the session. Unauthenticated requests to protected pages will be redirected to the login screen.
