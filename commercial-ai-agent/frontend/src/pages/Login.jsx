import React, { useState } from 'react';
import { LogIn, Sparkles } from 'lucide-react';
import { useGoogleLogin } from '@react-oauth/google';

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

export default function Login({ onLoginSuccess }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);

  const googleLogin = useGoogleLogin({
    flow: 'auth-code',
    scope: 'openid email profile https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/calendar',
    prompt: 'consent',
    onSuccess: async (codeResponse) => {
      setIsGoogleLoading(true);
      setError('');
      try {
        const response = await fetch(`${API_BASE_URL}/api/auth/google`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code: codeResponse.code }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
          throw new Error(data.error || 'Erreur de connexion avec Google');
        }
        
        onLoginSuccess(data.token, data.user);
      } catch (err) {
        setError(err.message);
      } finally {
        setIsGoogleLoading(false);
      }
    },
    onError: (errorResponse) => {
      setError('La connexion avec Google a échoué ou a été annulée.');
      console.error(errorResponse);
    }
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Erreur de connexion');
      }

      onLoginSuccess(data.token, data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-md-background px-4 overflow-hidden">
      {/* ── Organic Blur Shapes (MD3 signature) ── */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-32 -right-32 size-[500px] rounded-full bg-md-primary-container/40 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 size-[600px] rounded-[100px] rounded-tr-[20px] bg-md-tertiary-container/30 blur-3xl" />
        <div className="absolute top-1/3 left-1/4 size-80 rounded-full bg-md-secondary-container/25 blur-3xl" />
      </div>

      <div className="relative z-10 w-full max-w-[420px]">
        
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-5 grid size-14 place-items-center rounded-2xl bg-md-primary text-white shadow-md">
            <Sparkles className="size-7" />
          </div>
          <h1 className="text-3xl font-medium text-md-on-background tracking-tight">Bienvenue</h1>
          <p className="mt-2 text-sm text-md-on-surface-variant">Connectez-vous pour accéder à Commercial AI</p>
        </div>

        {/* Card */}
        <div className="rounded-[28px] bg-md-surface-container p-8 shadow-md">
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="rounded-2xl bg-md-error/10 p-3.5 text-sm text-md-error font-medium">
                {error}
              </div>
            )}
            
            {/* Email Field (MD3 Filled Text Field) */}
            <div className="space-y-1">
              <label className="text-xs font-medium text-md-on-surface-variant tracking-wide" htmlFor="email">
                Adresse email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@atlas.com"
                required
                className="input"
              />
            </div>

            {/* Password Field */}
            <div className="space-y-1">
              <label className="text-xs font-medium text-md-on-surface-variant tracking-wide" htmlFor="password">
                Mot de passe
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="input"
              />
            </div>

            {/* Submit Button (MD3 Filled Pill) */}
            <button
              type="submit"
              disabled={isLoading || isGoogleLoading || !email || !password}
              className="mt-3 flex w-full items-center justify-center gap-2 rounded-full bg-md-primary px-5 py-3.5 text-sm font-medium text-md-on-primary shadow-sm transition-all duration-300 ease-[cubic-bezier(0.2,0,0,1)] hover:bg-md-primary/90 hover:shadow-md disabled:opacity-50 disabled:hover:shadow-sm active:scale-95"
            >
              {isLoading ? (
                <span className="thinking-dots"><i /><i /><i /></span>
              ) : (
                <>
                  Se connecter
                  <LogIn className="size-4" />
                </>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="my-7 flex items-center justify-center space-x-3">
            <div className="h-px w-full bg-md-outline-variant"></div>
            <span className="text-xs font-medium text-md-on-surface-variant uppercase tracking-wider whitespace-nowrap">ou</span>
            <div className="h-px w-full bg-md-outline-variant"></div>
          </div>

          {/* Google Button (MD3 Outlined Pill) */}
          <button
            type="button"
            onClick={() => googleLogin()}
            disabled={isLoading || isGoogleLoading}
            className="flex w-full items-center justify-center gap-3 rounded-full border border-md-outline px-5 py-3.5 text-sm font-medium text-md-on-surface transition-all duration-300 ease-[cubic-bezier(0.2,0,0,1)] hover:bg-md-primary/5 disabled:opacity-50 active:scale-95"
          >
            {isGoogleLoading ? (
              <span className="thinking-dots"><i /><i /><i /></span>
            ) : (
              <>
                <svg className="size-5" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                </svg>
                Continuer avec Google
              </>
            )}
          </button>
        </div>

      </div>
    </div>
  );
}
