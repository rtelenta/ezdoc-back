# Cognito Authentication Setup Guide

## Overview

Users are authenticated via AWS Cognito. On their first API request, a user profile is automatically created in your database.

## Setup Steps

### 1. Install Dependencies

```bash
pip install python-jose[cryptography] requests
```

### 2. Configure Environment Variables

Create a `.env` file with your Cognito settings:

```env
COGNITO_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
```

Get these values from your AWS Cognito User Pool:

- **User Pool ID**: Found in Cognito User Pool > General Settings
- **App Client ID**: Found in Cognito User Pool > App Clients

### 3. Run Database Migration

```bash
alembic upgrade head
```

This creates the `users` table in your database.

### 4. Start Server

```bash
fastapi dev app/main.py
```

## Frontend Integration

### Setup react-oidc-context

```bash
npm install react-oidc-context oidc-client-ts
```

### Configure Auth Provider

```jsx
import { AuthProvider } from "react-oidc-context";

const cognitoAuthConfig = {
  authority: `https://cognito-idp.${COGNITO_REGION}.amazonaws.com/${COGNITO_USER_POOL_ID}`,
  client_id: COGNITO_APP_CLIENT_ID,
  redirect_uri: window.location.origin + "/callback",
  response_type: "code",
  scope: "openid profile email",
};

function App() {
  return (
    <AuthProvider {...cognitoAuthConfig}>
      <YourApp />
    </AuthProvider>
  );
}
```

### Make Authenticated API Calls

```jsx
import { useAuth } from "react-oidc-context";

function MyComponent() {
  const auth = useAuth();

  const fetchTemplates = async () => {
    const response = await fetch("http://localhost:8000/api/templates/", {
      headers: {
        Authorization: `Bearer ${auth.user.access_token}`,
        "Content-Type": "application/json",
      },
    });
    return response.json();
  };

  return (
    <div>
      {auth.isAuthenticated ? (
        <button onClick={fetchTemplates}>Load Templates</button>
      ) : (
        <button onClick={() => auth.signinRedirect()}>Sign In</button>
      )}
    </div>
  );
}
```

## How It Works

### User Flow

1. **User signs up** in Cognito (via Hosted UI or custom form)
2. **User logs in** → react-oidc-context receives JWT tokens
3. **First API request** → Backend validates token and creates user in DB
4. **Subsequent requests** → Backend validates token and retrieves user from DB

### Token Validation

- Frontend sends: `Authorization: Bearer {access_token}`
- Backend verifies token signature using Cognito's public keys (JWKS)
- Backend extracts user info (user_id, email) from validated token
- Backend ensures user exists in database (auto-creates on first request)

## API Endpoints

### Protected Endpoints (Require Authentication)

All these endpoints require `Authorization: Bearer {token}` header:

- `POST /api/templates/` - Create template
- `GET /api/templates/` - List templates
- `GET /api/templates/{id}` - Get template
- `GET /api/templates/view/{id}` - View template as PDF
- `DELETE /api/templates/{id}` - Delete template

### User Profile Endpoints

- `GET /api/users/me` - Get current user profile
- `PATCH /api/users/me` - Update current user profile

## Testing Authentication

### Get Access Token (for testing)

Use AWS Cognito Hosted UI or AWS CLI:

```bash
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id YOUR_CLIENT_ID \
  --auth-parameters USERNAME=user@example.com,PASSWORD=yourpassword
```

### Test with cURL

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  http://localhost:8000/api/users/me
```

## Database Schema

### users Table

- `cognito_user_id` (PK) - Cognito 'sub' claim
- `email` - User's email (unique, indexed)
- `full_name` - User's full name
- `job_title` - Optional job title
- `summary` - Optional bio/summary
- `department` - Optional department
- `profile_picture_url` - Optional profile picture
- `created_at` - When user first made API request
- `updated_at` - Last profile update
- `last_login_at` - Last API request timestamp

## Security Notes

- Tokens expire after 1 hour (configurable in Cognito)
- Token signature is verified using Cognito's public keys
- JWKS (public keys) are cached for performance
- Invalid/expired tokens return 401 Unauthorized
- Users are automatically created on first API request
