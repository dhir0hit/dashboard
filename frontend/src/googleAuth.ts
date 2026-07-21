// Frontend-only Google OAuth (Authorization Code + PKCE, no client_secret).
//
// Requires a Google OAuth client of type "Desktop app" (NOT "Web application")
// in Google Cloud Console → APIs & Services → Credentials. Desktop clients
// don't have a secret and allow the browser to exchange the code directly with
// Google's token endpoint using PKCE. Web-application-type clients require
// a secret at exchange time, which would force us back through the backend.
//
// Lifecycle (same-tab redirect; chosen over the popup variant for simplicity):
//   1. On "Connect Google" click, generate `code_verifier` (random) + state.
//   2. Compute `code_challenge = base64url(SHA-256(code_verifier))`.
//   3. Redirect the whole page to Google's consent screen.
//   4. On returning to /calendar?code=...&state=..., verify state, then POST
//      {code, code_verifier, redirect_uri, grant_type=authorization_code} to
//      https://oauth2.googleapis.com/token (no client_secret needed).
//   5. Persist access_token + refresh_token + expires_at + email in
//      localStorage. Expose helpers to read/refresh/clear them.
//   6. When the calendar page calls /api/calendar/google/sync, it passes
//      the access_token as `Authorization: Bearer <token>`; the backend never
//      sees the secret or the refresh_token.
//
// Refresh: when access_token is expired, we call the token endpoint with
// grant_type=refresh_token (no secret needed for Desktop clients).

const STORAGE_KEY = "dashboard.google.tokens.v1";
const VERIFIER_KEY = "dashboard.google.pkce.verifier";
const STATE_KEY = "dashboard.google.pkce.state";

const GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth";
const GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token";
const GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo";

// Calendar.readonly + email (for showing "Signed in as <email>").
const DEFAULT_SCOPE = "https://www.googleapis.com/auth/calendar.readonly email";

export interface GoogleTokens {
  access_token: string;
  refresh_token?: string | null;
  expires_at: string; // ISO 8601
  email?: string | null;
  scope?: string | null;
}

// --- PKCE helpers --------------------------------------------------------

function randomString(len: number): string {
  const bytes = new Uint8Array(len);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

function base64url(bytes: ArrayBuffer): string {
  const arr = new Uint8Array(bytes);
  let s = "";
  for (let i = 0; i < arr.length; i++) s += String.fromCharCode(arr[i]);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function sha256(input: string): Promise<ArrayBuffer> {
  const data = new TextEncoder().encode(input);
  return await crypto.subtle.digest("SHA-256", data);
}

// --- Storage -------------------------------------------------------------

export function getStoredTokens(): GoogleTokens | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as GoogleTokens;
    if (!parsed?.access_token || !parsed.expires_at) return null;
    return parsed;
  } catch {
    return null;
  }
}

function storeTokens(t: GoogleTokens): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(t));
}

export function clearStoredTokens(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export function isExpired(t: GoogleTokens, skewSeconds = 60): boolean {
  try {
    const exp = new Date(t.expires_at).getTime();
    return Date.now() + skewSeconds * 1000 >= exp;
  } catch {
    return true;
  }
}

// --- Public client config -----------------------------------------------

// The frontend needs the Google OAuth client_id (Desktop-app type). It's
// not secret — Desktop clients have no secret by design. Configure it via
// VITE_GOOGLE_CLIENT_ID at build/dev time. The redirect URI is computed
// from the current origin so the same build works in dev (:5173) and prod
// (:8888) without per-env config.
export function getGoogleClientId(): string {
  return import.meta.env.VITE_GOOGLE_CLIENT_ID ?? "";
}

export function getRedirectUri(): string {
  // Always point at the /calendar route on the current origin. Google
  // accepts any http://localhost:<port> redirect URI for Desktop-app
  // clients without pre-registration.
  return `${window.location.origin}/calendar`;
}

export function isGoogleConfigured(): boolean {
  return !!getGoogleClientId();
}

// --- Build auth URL & kick off redirect ---------------------------------

export async function beginGoogleLogin(): Promise<void> {
  const client_id = getGoogleClientId();
  if (!client_id) {
    throw new Error(
      "VITE_GOOGLE_CLIENT_ID is not set. Create a Desktop-app OAuth client in Google Cloud Console and set VITE_GOOGLE_CLIENT_ID."
    );
  }
  const verifier = randomString(32);
  const state = randomString(16);
  const challenge = base64url(await sha256(verifier));

  sessionStorage.setItem(VERIFIER_KEY, verifier);
  sessionStorage.setItem(STATE_KEY, state);

  const params = new URLSearchParams({
    client_id,
    redirect_uri: getRedirectUri(),
    response_type: "code",
    scope: DEFAULT_SCOPE,
    access_type: "offline", // request refresh_token
    prompt: "consent", // force consent so refresh_token is returned each time
    code_challenge: challenge,
    code_challenge_method: "S256",
    state,
  });
  window.location.assign(`${GOOGLE_AUTH_URL}?${params.toString()}`);
}

// --- Handle ?code= on return --------------------------------------------

interface ExchangeResult {
  ok: boolean;
  email: string | null;
  error?: string;
}

export async function handleGoogleRedirect(): Promise<ExchangeResult> {
  const url = new URL(window.location.href);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const errParam = url.searchParams.get("error");

  // Clean the query string so a refresh doesn't re-trigger the exchange.
  url.searchParams.delete("code");
  url.searchParams.delete("state");
  url.searchParams.delete("error");
  window.history.replaceState({}, "", url.toString());

  if (errParam) {
    return { ok: false, email: null, error: `Google returned error: ${errParam}` };
  }
  if (!code) return { ok: false, email: null, error: "No code in callback." };

  const savedState = sessionStorage.getItem(STATE_KEY);
  const verifier = sessionStorage.getItem(VERIFIER_KEY);
  sessionStorage.removeItem(STATE_KEY);
  sessionStorage.removeItem(VERIFIER_KEY);

  if (!savedState || !verifier) {
    return { ok: false, email: null, error: "PKCE state lost (session expired?). Try again." };
  }
  if (state !== savedState) {
    return { ok: false, email: null, error: "OAuth state mismatch — possible CSRF." };
  }

  const client_id = getGoogleClientId();
  const redirect_uri = getRedirectUri();

  // Exchange code for tokens. Desktop-app clients do NOT require
  // client_secret at this endpoint — PKCE (code_verifier) is the proof.
  const body = new URLSearchParams({
    code,
    client_id,
    redirect_uri,
    grant_type: "authorization_code",
    code_verifier: verifier,
  });

  let resp: Response;
  try {
    resp = await fetch(GOOGLE_TOKEN_URL, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
  } catch (e) {
    return { ok: false, email: null, error: `Network error exchanging code: ${(e as Error).message}` };
  }

  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    return { ok: false, email: null, error: `Token exchange failed (${resp.status}): ${text}` };
  }

  const tokens = (await resp.json()) as {
    access_token: string;
    refresh_token?: string;
    expires_in: number;
    scope?: string;
  };

  // Fetch the user's email so we can show "Signed in as <email>".
  let email: string | null = null;
  try {
    const ui = await fetch(GOOGLE_USERINFO_URL, {
      headers: { Authorization: `Bearer ${tokens.access_token}` },
    });
    if (ui.ok) email = (await ui.json()).email ?? null;
  } catch {
    // email is best-effort — keep going without it
  }

  const expires_at = new Date(Date.now() + (tokens.expires_in ?? 3600) * 1000).toISOString();
  const stored: GoogleTokens = {
    access_token: tokens.access_token,
    refresh_token: tokens.refresh_token ?? null,
    expires_at,
    email,
    scope: tokens.scope ?? null,
  };
  storeTokens(stored);
  return { ok: true, email };
}

// --- Get a valid (possibly refreshed) access token -----------------------

export async function getValidAccessToken(): Promise<string | null> {
  const t = getStoredTokens();
  if (!t) return null;
  if (!isExpired(t)) return t.access_token;

  if (!t.refresh_token) {
    // Can't refresh silently — user must click "Connect Google" again.
    return null;
  }

  const client_id = getGoogleClientId();
  const body = new URLSearchParams({
    client_id,
    refresh_token: t.refresh_token,
    grant_type: "refresh_token",
  });

  const resp = await fetch(GOOGLE_TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!resp.ok) {
    clearStoredTokens();
    return null;
  }
  const data = await resp.json();
  const expires_at = new Date(Date.now() + (data.expires_in ?? 3600) * 1000).toISOString();
  const refreshed: GoogleTokens = {
    access_token: data.access_token,
    refresh_token: t.refresh_token, // Google does not return a new refresh_token here
    expires_at,
    email: t.email,
    scope: t.scope,
  };
  storeTokens(refreshed);
  return refreshed.access_token;
}