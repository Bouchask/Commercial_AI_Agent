import React, { useState } from 'react';
import { LogIn, Sparkles, Zap, BarChart3, Mail, Calendar } from 'lucide-react';
import { useGoogleLogin } from '@react-oauth/google';

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

const features = [
  { icon: Zap, label: "Devis instantanés", desc: "Générez des devis professionnels en quelques secondes" },
  { icon: Mail, label: "Email intégré", desc: "Envoyez des emails directement via Gmail en votre nom" },
  { icon: Calendar, label: "Gestion Agenda", desc: "Planifiez des réunions avec vos clients automatiquement" },
  { icon: BarChart3, label: "Suivi commercial", desc: "Synchronisez tout avec Google Sheets en temps réel" },
];

export default function Login({ onLoginSuccess }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);

  const googleLogin = useGoogleLogin({
    flow: 'auth-code',
    scope: 'openid email profile https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/gmail.send',
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
        if (!response.ok) throw new Error(data.error || 'Erreur de connexion avec Google');
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
      if (!response.ok) throw new Error(data.error || 'Erreur de connexion');
      onLoginSuccess(data.token, data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen overflow-hidden bg-[#080B14]">
      
      {/* ── Animated Background Orbs ── */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="orb-1 absolute -top-40 -left-40 size-[600px] rounded-full opacity-30"
          style={{ background: "radial-gradient(circle, #7C3AED 0%, transparent 70%)", filter: "blur(60px)" }} />
        <div className="orb-2 absolute top-1/3 right-0 size-[500px] rounded-full opacity-20"
          style={{ background: "radial-gradient(circle, #4F46E5 0%, transparent 70%)", filter: "blur(80px)" }} />
        <div className="orb-3 absolute -bottom-40 left-1/3 size-[400px] rounded-full opacity-25"
          style={{ background: "radial-gradient(circle, #06B6D4 0%, transparent 70%)", filter: "blur(60px)" }} />
        {/* Grid pattern */}
        <div className="grid-pattern absolute inset-0 opacity-40" />
      </div>

      {/* ── LEFT SIDE: Hero ── */}
      <div className="relative hidden lg:flex lg:w-1/2 flex-col justify-between p-12">
        <div>
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-600 shadow-lg shadow-violet-500/30">
              <Sparkles className="size-5 text-white" />
            </div>
            <span className="text-lg font-bold text-white tracking-tight">Commercial AI</span>
          </div>

          {/* Hero Text */}
          <div className="mt-20">
            <h1 className="text-5xl font-extrabold leading-tight tracking-tight text-white">
              Votre assistant
              <br />
              <span className="gradient-text">commercial IA</span>
            </h1>
            <p className="mt-6 text-lg text-slate-400 leading-relaxed max-w-md">
              Automatisez vos devis, emails clients, et suivis commerciaux. 
              Propulsé par l'intelligence artificielle et connecté à votre Google Workspace.
            </p>
          </div>

          {/* Features */}
          <div className="mt-12 space-y-4">
            {features.map((f, i) => (
              <div key={i} className="flex items-start gap-4">
                <div className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-xl border border-violet-500/20 bg-violet-500/10">
                  <f.icon className="size-4 text-violet-400" />
                </div>
                <div>
                  <div className="text-sm font-semibold text-slate-200">{f.label}</div>
                  <div className="text-sm text-slate-500">{f.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom quote */}
        <p className="text-xs text-slate-600">
          En vous connectant, vous acceptez notre{' '}
          <a href="/privacy" className="text-violet-500 hover:text-violet-400 transition-colors">politique de confidentialité</a>
          {' '}et nos{' '}
          <a href="/terms" className="text-violet-500 hover:text-violet-400 transition-colors">conditions d'utilisation</a>.
        </p>
      </div>

      {/* ── RIGHT SIDE: Login Form ── */}
      <div className="relative flex w-full items-center justify-center px-6 lg:w-1/2">
        <div className="w-full max-w-[420px]">
          
          {/* Mobile logo */}
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="grid size-9 place-items-center rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-600 shadow-lg shadow-violet-500/30">
              <Sparkles className="size-4 text-white" />
            </div>
            <span className="text-base font-bold text-white">Commercial AI</span>
          </div>

          {/* Card */}
          <div className="rounded-3xl border border-white/8 bg-[#111827]/80 p-8 shadow-2xl backdrop-blur-xl"
            style={{ boxShadow: "0 25px 50px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05)" }}>
            
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-white">Connexion</h2>
              <p className="mt-2 text-sm text-slate-400">Accédez à votre espace commercial</p>
            </div>

            {error && (
              <div className="mb-5 flex items-center gap-2.5 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                <span className="size-4 shrink-0">⚠</span>
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-500" htmlFor="email">
                  Adresse email
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="vous@exemple.com"
                  required
                  className="input"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-500" htmlFor="password">
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

              <button
                type="submit"
                disabled={isLoading || isGoogleLoading || !email || !password}
                className="btn-primary mt-2 w-full py-3"
              >
                {isLoading ? (
                  <span className="thinking-dots"><i /><i /><i /></span>
                ) : (
                  <>
                    <LogIn className="size-4" />
                    Se connecter
                  </>
                )}
              </button>
            </form>

            {/* Divider */}
            <div className="my-6 flex items-center gap-3">
              <div className="h-px flex-1 bg-white/6" />
              <span className="text-xs font-medium uppercase tracking-wider text-slate-600">ou</span>
              <div className="h-px flex-1 bg-white/6" />
            </div>

            {/* Google Button */}
            <button
              type="button"
              onClick={() => googleLogin()}
              disabled={isLoading || isGoogleLoading}
              className="group flex w-full items-center justify-center gap-3 rounded-xl border border-white/8 bg-white/4 px-5 py-3 text-sm font-medium text-slate-300 transition-all duration-200 hover:border-white/15 hover:bg-white/8 hover:text-white disabled:opacity-40 active:scale-[0.98]"
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

            {/* Legal links - mobile */}
            <div className="mt-6 flex flex-wrap items-center justify-center gap-4 text-xs text-slate-600 lg:hidden">
              <a href="/privacy" className="hover:text-violet-400 transition-colors">Confidentialité</a>
              <span>•</span>
              <a href="/terms" className="hover:text-violet-400 transition-colors">Conditions</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
