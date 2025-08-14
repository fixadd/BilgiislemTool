# BilgiislemTool

## Environment Variables

The application initializes an administrator account using credentials supplied via environment variables.

- `ADMIN_USERNAME` – Username for the initial administrator.
- `ADMIN_PASSWORD` – Password for the initial administrator.

Both variables must be defined before the application starts. If either variable is missing, the application will exit with an error instead of creating the admin user.

When using Docker Compose, provide these variables in your environment or an `.env` file:

```
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_admin_password
```

## Authentication

Administrative pages now require users to be authenticated. Visit `/login` to sign in and `/logout` to terminate the session. Unauthenticated requests to protected pages will be redirected to the login screen.
