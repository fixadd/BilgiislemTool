# BilgiislemTool

## Environment Variables

The application initializes an administrator account using credentials supplied via environment variables and requires a secret key for session handling.

- `ADMIN_USERNAME` – Username for the initial administrator.
- `ADMIN_PASSWORD` – Password for the initial administrator.
- `SESSION_SECRET` – Secret key used to sign session cookies.

All three variables must be defined before the application starts. If any variable is missing, the application will exit with an error instead of creating the admin user or starting the server.

When using Docker Compose, provide these variables in your environment or an `.env` file:

```
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_admin_password
SESSION_SECRET=some_long_random_string
```

## Authentication

Administrative pages now require users to be authenticated. Visit `/login` to sign in and `/logout` to terminate the session. Unauthenticated requests to protected pages will be redirected to the login screen.
