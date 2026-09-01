import hs, { createHydroServer } from '@hydroserver/client'

// The HydroServer instance to test against. Override with VITE_APP_HOST if
// you're pointing this at a different deployment.
const HOST = import.meta.env.VITE_APP_HOST || 'http://127.0.0.1:8000'

// Must match a client registered on that instance (see README note in chat /
// the app's console output for the exact redirect URI to register).
const CLIENT_ID = import.meta.env.VITE_APP_OIDC_CLIENT_ID || 'oidc-test-client'

const app = document.getElementById('app')!

function render(html: string) {
  app.innerHTML = html
}

async function main() {
  // Exchange the authorization code for tokens, then bounce back to '/'.
  if (window.location.pathname === '/callback') {
    render('<p>Completing sign-in…</p>')
    await createHydroServer({ host: HOST, oidc: { clientId: CLIENT_ID } })
    try {
      await hs.session.completeLogin()
    } catch (error) {
      render(`<h1>Sign-in failed</h1><pre>${String(error)}</pre>`)
      return
    }
    window.location.replace('/')
    return
  }

  await createHydroServer({ host: HOST, oidc: { clientId: CLIENT_ID } })

  if (!hs.session.isAuthenticated) {
    render(`
      <h1>HydroServer OIDC Test Client</h1>
      <p class="muted">Host: ${HOST}</p>
      <button id="login">Log in</button>
    `)
    document.getElementById('login')!.addEventListener('click', () => {
      void hs.session.login()
    })
    return
  }

  render('<p>Loading user info…</p>')

  const [userRes, workspaces] = await Promise.all([
    hs.user.get(),
    hs.workspaces.listAllItems({ is_associated: true }),
  ])

  render(`
    <h1>HydroServer OIDC Test Client</h1>
    <p class="muted">Host: ${HOST}</p>
    <button id="logout">Log out</button>

    <h2>User</h2>
    <pre>${userRes.ok ? JSON.stringify(userRes.data, null, 2) : `Error: ${userRes.message}`}</pre>

    <h2>Workspaces (${workspaces.length})</h2>
    <pre>${JSON.stringify(workspaces, null, 2)}</pre>
  `)

  document.getElementById('logout')!.addEventListener('click', () => {
    void hs.session.logout()
  })
}

void main()