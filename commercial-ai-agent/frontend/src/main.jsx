import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

import { GoogleOAuthProvider } from '@react-oauth/google';

const configuredClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

function Root() {
  const [clientId, setClientId] = useState(configuredClientId);

  useEffect(() => {
    if (clientId) return;
    fetch('/api/auth/google/config')
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('Google OAuth unavailable')))
      .then((data) => setClientId(data.client_id || ''))
      .catch(() => setClientId('unavailable'));
  }, [clientId]);

  if (!clientId) {
    return <main className="grid min-h-screen place-items-center">Chargement…</main>;
  }

  return (
    <GoogleOAuthProvider clientId={clientId === 'unavailable' ? 'unavailable' : clientId}>
      <App />
    </GoogleOAuthProvider>
  );
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Root />
  </StrictMode>,
)
