# OIDC Test Client

A minimal browser app for sanity-checking the OIDC login flow against a HydroServer
instance. Logs in via OIDC, then displays the authenticated user's info and the list of
workspaces they can see.

## Install and run

```bash
npm install
npm run dev
```

Visit `http://127.0.0.1:5001`.

By default the app points at `http://127.0.0.1:8000` (a local HydroServer dev server). To
test against a different instance, create a `.env.local` file in this directory:

```
VITE_APP_HOST=https://your-instance.example.com
VITE_APP_OIDC_CLIENT_ID=your-client-id
```

## Registering the client with HydroServer

Before logging in, register an OIDC client on the target HydroServer instance with:

- **Client ID:** `oidc-test-client` (or whatever you set `VITE_APP_OIDC_CLIENT_ID` to)
- **Type:** `public` — this is a browser app with no client secret. Registering it as
  `confidential` (the default) will break the token exchange.
- **Grant types:** `authorization_code`
- **Response types:** `code`
- **Scopes:** `openid`, `profile`, `email` — the client requests all three; anything not
  listed here will be silently dropped, and the User section below will be missing fields.
- **Redirect URI:** `http://127.0.0.1:5001/callback`
- **Post-logout redirect URI:** `http://127.0.0.1:5001/`

## Verifying it works

1. The landing page shows a **Log in** button.
2. Clicking it redirects to the HydroServer instance's login page.
3. After signing in, you're redirected back to `/callback`, which briefly shows
   "Completing sign-in…" and then bounces back to `/`.
4. The page now shows:
   - A **Log out** button.
   - A **User** section with the JSON returned from the OIDC userinfo endpoint (email,
     account type, etc.).
   - A **Workspaces** section listing the workspaces associated with the logged-in user,
     as raw JSON.

If any step fails, check the browser console first — cross-origin requests to the
HydroServer instance need CORS configured correctly on that instance.