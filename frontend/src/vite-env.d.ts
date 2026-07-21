/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  // Google OAuth client_id (Desktop-app type — no secret). Used by
  // src/googleAuth.ts to build the PKCE auth URL entirely in the browser.
  readonly VITE_GOOGLE_CLIENT_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}