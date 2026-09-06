import { lazy, Suspense, useState } from 'react';
import Login from './pages/Login';

// The dashboard contains the commercial workspace and its heavier UI
// dependencies. Loading it only after authentication keeps the login page
// responsive on slow connections.
const Dashboard = lazy(() => import('./pages/Dashboard'));

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('auth_token'));
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('auth_user');
    return saved ? JSON.parse(saved) : null;
  });

  const handleLogin = (newToken, newUser) => {
    localStorage.setItem('auth_token', newToken);
    localStorage.setItem('auth_user', JSON.stringify(newUser));
    setToken(newToken);
    setUser(newUser);
  };

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    setToken(null);
    setUser(null);
  };

  if (!token) {
    return <Login onLoginSuccess={handleLogin} />;
  }

  return (
    <Suspense fallback={<main className="grid min-h-screen place-items-center bg-md-background text-md-on-surface">Chargement…</main>}>
      <Dashboard user={user} onLogout={handleLogout} />
    </Suspense>
  );
}

export default App;
