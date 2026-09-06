import React, { useEffect, useRef, useState } from "react";
import { Toaster, toast } from 'sonner';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowUp,
  Bot,
  ChevronDown,
  CircleHelp,
  Menu,
  MessageSquarePlus,
  Paperclip,
  Plus,
  Search,
  Settings,
  Sparkles,
  Table,
  UserRound,
  X,
} from "lucide-react";
import { ChatMessage } from "../components/ui/ChatMessage";

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

const WELCOME_MESSAGE = {
  role: "agent",
  content:
    "Bonjour ! Je peux préparer un devis, rechercher vos prestations et envoyer un email après votre validation.",
};

const SUGGESTIONS = [
  "Crée un devis pour Atlas E-Commerce Group avec un site e-commerce et une optimisation SEO.",
  "Prépare un devis pour un site vitrine avec 6 mois de maintenance.",
  "Quels services sont disponibles dans le catalogue ?",
];

const RECENT_CHATS = [
  "Devis Atlas E-Commerce",
  "Proposition de maintenance",
  "Catalogue des services",
];

/* ═══════════════════════════════════════════════════════
   SIDEBAR — MD3 Navigation Drawer
   ═══════════════════════════════════════════════════════ */
function Sidebar({ open, onClose, onNewChat, user, onLogout, setView, spreadsheetId, conversations, activeThreadId, onSelectConversation }) {
  return (
    <aside
      className={`fixed inset-y-0 left-0 z-40 flex w-[280px] flex-col bg-md-surface-container p-3 transition-transform duration-300 ease-[cubic-bezier(0.2,0,0,1)] md:static md:translate-x-0 ${
        open ? "translate-x-0" : "-translate-x-full"
      }`}
    >
      {/* Logo */}
      <div className="flex items-center justify-between px-2 py-2">
        <div className="flex items-center gap-2.5 text-sm font-medium text-md-on-surface">
          <span className="grid size-8 place-items-center rounded-2xl bg-md-primary text-white shadow-sm">
            <Sparkles className="size-4" />
          </span>
          Commercial AI
        </div>
        <button onClick={onClose} className="icon-button md:hidden" aria-label="Fermer le menu">
          <X className="size-4" />
        </button>
      </div>

      {/* New Chat */}
      <button onClick={() => { onNewChat(); setView('chat'); }} className="new-chat-button">
        <MessageSquarePlus className="size-[18px]" />
        Nouvelle discussion
      </button>

      {/* Navigation */}
      <div className="mt-5 flex-1 overflow-y-auto px-1">
        <div className="sidebar-label">Navigation</div>
        <div className="mt-1 space-y-1">
          <button onClick={() => setView('clients')} className="sidebar-chat">
            <UserRound className="size-4 shrink-0" /> Clients
          </button>
          <button onClick={() => setView('services')} className="sidebar-chat">
            <Settings className="size-4 shrink-0" /> Services
          </button>
          <button onClick={() => setView('quotes')} className="sidebar-chat">
            <Bot className="size-4 shrink-0" /> Devis
          </button>
          <button onClick={() => setView('invoices')} className="sidebar-chat">
            <Table className="size-4 shrink-0" /> Factures
          </button>
          <button onClick={() => setView('assignments')} className="sidebar-chat">
            <Plus className="size-4 shrink-0" /> Assignations
          </button>
        </div>

        {/* Quick Access */}
        <div className="sidebar-label mt-5">Accès Rapide</div>
        <div className="mt-1 space-y-1">
          <button
            onClick={() => {
              if (!spreadsheetId) {
                toast.error("Aucun tableur Google Sheets créé. Demandez à l'agent de créer un export pour le générer !");
                return;
              }
              setView('sheets');
              if (window.innerWidth < 768) onClose();
            }}
            className={`sidebar-chat ${
              spreadsheetId
                ? "bg-md-secondary-container/40 text-md-primary"
                : "text-md-outline cursor-not-allowed"
            }`}
          >
            <Table className="size-4 shrink-0" />
            <span className="truncate">Base de Données (Sheets)</span>
          </button>
        </div>

        {/* Recent Chats */}
        <div className="sidebar-label mt-5">Récentes</div>
        <div className="mt-1 space-y-1">
          {conversations.map((chat) => (
            <button 
              key={chat.id} 
              onClick={() => { onSelectConversation(chat.id); if (window.innerWidth < 768) onClose(); }}
              className={`sidebar-chat ${chat.id === activeThreadId ? "sidebar-chat-active" : ""}`}
            >
              <Bot className="size-4 shrink-0" />
              <span className="truncate">{chat.title || "Discussion"}</span>
            </button>
          ))}
          {conversations.length === 0 && (
            <div className="text-xs text-md-on-surface-variant/60 px-3 py-2">
              Aucune discussion
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="space-y-1 border-t border-md-outline-variant/50 pt-3">
        <button className="sidebar-chat">
          <CircleHelp className="size-4" /> Aide
        </button>
        <button className="sidebar-chat">
          <Settings className="size-4" /> Paramètres
        </button>
        <button onClick={onLogout} className="mt-1 flex w-full items-center gap-2.5 rounded-full px-3 py-2.5 text-left text-sm text-md-on-surface-variant hover:bg-md-error/10 hover:text-md-error transition-all duration-200 active:scale-[0.98]">
          <span className="grid size-8 place-items-center rounded-full bg-md-primary text-xs font-medium text-md-on-primary">
            {user?.email?.[0]?.toUpperCase() || 'U'}
          </span>
          <span className="min-w-0 flex-1 truncate">{user?.email || 'Utilisateur'}</span>
          <span className="text-xs text-md-on-surface-variant/60">Déconnexion</span>
        </button>
      </div>
    </aside>
  );
}

/* ═══════════════════════════════════════════════════════
   CLIENTS PANEL
   ═══════════════════════════════════════════════════════ */
function ClientsPanel() {
  const [clients, setClients] = useState([]);
  const [name, setName] = useState("");
  const token = localStorage.getItem('auth_token');

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const r = await fetch(`${API_BASE_URL}/api/clients`, { headers: { ...(token ? { Authorization: 'Bearer ' + token } : {}) } });
        if (!r.ok) return;
        const data = await r.json();
        if (mounted) setClients(data || []);
      } catch (e) {
        console.warn('clients fetch', e.message);
      }
    })();
    return () => { mounted = false; };
  }, [token]);

  const createClient = async () => {
    if (!name.trim()) return toast.error("Le nom du client est requis");
    try {
      const r = await fetch(`${API_BASE_URL}/api/clients`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) },
        body: JSON.stringify({ name }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || 'Erreur');
      setClients((c) => [data, ...c]);
      setName('');
      toast.success("Client créé avec succès !");
    } catch (e) {
      toast.error('Création client échouée: ' + e.message);
    }
  };

  return (
    <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: [0.2, 0, 0, 1] }}>
      <h2 className="mb-6 text-2xl font-medium text-md-on-surface">Clients</h2>
      <div className="glass-panel mb-8">
        <h3 className="mb-4 text-xs font-medium uppercase tracking-wider text-md-primary">Nouveau Client</h3>
        <div className="flex flex-col sm:flex-row gap-3">
          <input value={name} onChange={(e) => setName(e.target.value)} className="input flex-1" placeholder="Nom de l'entreprise ou du client" />
          <button onClick={createClient} className="btn-primary">
            <Plus className="size-4" /> Ajouter
          </button>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <AnimatePresence>
          {clients.map((c, i) => (
            <motion.div key={c.id} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: Math.min(i * 0.05, 0.5), ease: [0.2, 0, 0, 1] }} className="list-item-glass">
              <div className="flex items-center gap-3">
                <div className="grid size-10 shrink-0 place-items-center rounded-full bg-md-primary-container text-md-on-primary-container">
                  <UserRound className="size-5" />
                </div>
                <div className="min-w-0">
                  <div className="font-medium text-md-on-surface truncate">{c.name || c.company || 'Client sans nom'}</div>
                  <div className="text-xs text-md-on-surface-variant">ID: {c.id}</div>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </motion.section>
  );
}

/* ═══════════════════════════════════════════════════════
   SERVICES PANEL
   ═══════════════════════════════════════════════════════ */
function ServicesPanel() {
  const [services, setServices] = useState([]);
  const [title, setTitle] = useState('');
  const [price, setPrice] = useState('');
  const token = localStorage.getItem('auth_token');

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const r = await fetch(`${API_BASE_URL}/api/services`, { headers: { ...(token ? { Authorization: 'Bearer ' + token } : {}) } });
        if (!r.ok) return;
        const data = await r.json();
        if (mounted) setServices(data || []);
      } catch (e) {
        console.warn('services fetch', e.message);
      }
    })();
    return () => { mounted = false; };
  }, [token]);

  const createService = async () => {
    if (!title.trim() || !price) return toast.error("Tous les champs sont requis");
    try {
      const r = await fetch(`${API_BASE_URL}/api/services`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) },
        body: JSON.stringify({ title, price: Number(price) }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || 'Erreur');
      setServices((s) => [data, ...s]);
      setTitle(''); setPrice('');
      toast.success("Service ajouté au catalogue !");
    } catch (e) {
      toast.error('Création service échouée: ' + e.message);
    }
  };

  return (
    <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: [0.2, 0, 0, 1] }}>
      <h2 className="mb-6 text-2xl font-medium text-md-on-surface">Catalogue de Services</h2>
      <div className="glass-panel mb-8">
        <h3 className="mb-4 text-xs font-medium uppercase tracking-wider text-md-primary">Nouveau Service</h3>
        <div className="flex flex-col sm:flex-row gap-3">
          <input value={title} onChange={(e) => setTitle(e.target.value)} className="input flex-1" placeholder="Intitulé du service (ex: Création Site Web)" />
          <input type="number" value={price} onChange={(e) => setPrice(e.target.value)} className="input sm:w-32" placeholder="Prix (€)" />
          <button onClick={createService} className="btn-primary">
            <Plus className="size-4" /> Ajouter
          </button>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <AnimatePresence>
          {services.map((s, i) => (
            <motion.div key={s.id} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: Math.min(i * 0.05, 0.5), ease: [0.2, 0, 0, 1] }} className="list-item-glass flex-row items-center justify-between">
              <span className="font-medium text-md-on-surface truncate pr-2">{s.name || s.title}</span>
              <span className="shrink-0 rounded-full bg-md-primary-container px-3 py-1 text-sm font-medium text-md-on-primary-container">
                {s.price ?? s.unit_price} €
              </span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </motion.section>
  );
}

/* ═══════════════════════════════════════════════════════
   QUOTES PANEL
   ═══════════════════════════════════════════════════════ */
function QuotesPanel() {
  const token = localStorage.getItem('auth_token');
  const [quotes, setQuotes] = useState([]);
  const [clients, setClients] = useState([]);
  const [services, setServices] = useState([]);
  const [clientId, setClientId] = useState('');
  const [items, setItems] = useState([{ service_id: '', quantity: 1, unit_price: 0 }]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const [rq, rc, rs] = await Promise.all([
          fetch(`${API_BASE_URL}/api/quotes`, { headers: { ...(token ? { Authorization: 'Bearer ' + token } : {}) } }),
          fetch(`${API_BASE_URL}/api/clients`, { headers: { ...(token ? { Authorization: 'Bearer ' + token } : {}) } }),
          fetch(`${API_BASE_URL}/api/services`, { headers: { ...(token ? { Authorization: 'Bearer ' + token } : {}) } }),
        ]);
        if (rq.ok) { const q = await rq.json(); if (mounted) setQuotes(q || []); }
        if (rc.ok) { const c = await rc.json(); if (mounted) setClients(c || []); }
        if (rs.ok) { const s = await rs.json(); if (mounted) setServices(s || []); }
      } catch (e) { console.warn('quotes init', e.message); }
    })();
    return () => { mounted = false; };
  }, [token]);

  const addItem = () => setItems((it) => [...it, { service_id: '', quantity: 1, unit_price: 0 }]);
  const updateItem = (idx, key, value) => setItems((it) => it.map((itx, i) => i === idx ? { ...itx, [key]: value } : itx));
  
  const handleServiceSelect = (idx, serviceId) => {
    const s = services.find(x => x.id.toString() === serviceId);
    setItems((it) => it.map((itx, i) => i === idx ? { ...itx, service_id: serviceId, unit_price: s ? (s.price ?? s.unit_price) : 0 } : itx));
  };

  const createQuote = async () => {
    if (!clientId) return toast.error('Veuillez sélectionner un client');
    const payload = { client_id: clientId, items: items.map(i => ({ service_id: i.service_id, quantity: Number(i.quantity), unit_price: Number(i.unit_price) })) };
    try {
      const r = await fetch(`${API_BASE_URL}/api/quotes`, { method: 'POST', headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) }, body: JSON.stringify(payload) });
      const d = await r.json(); if (!r.ok) throw new Error(d.error || 'Erreur');
      setQuotes((q) => [d, ...q]);
      setItems([{ service_id: '', quantity: 1, unit_price: 0 }]); setClientId('');
      toast.success("Devis créé avec succès !");
    } catch (e) { toast.error('Création devis échouée: ' + e.message); }
  };

  return (
    <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: [0.2, 0, 0, 1] }}>
      <h2 className="mb-6 text-2xl font-medium text-md-on-surface">Gestion des Devis</h2>
      <div className="glass-panel mb-8">
        <h3 className="mb-4 text-xs font-medium uppercase tracking-wider text-md-primary">Créer un nouveau devis</h3>
        <select value={clientId} onChange={(e) => setClientId(e.target.value)} className="input mb-4">
          <option value="">Sélectionner un client</option>
          {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        
        <div className="space-y-3 border-l-2 border-md-primary/30 pl-4 py-1">
          {items.map((it, idx) => (
            <div key={idx} className="flex flex-col sm:flex-row gap-2">
              <select value={it.service_id} onChange={(e) => handleServiceSelect(idx, e.target.value)} className="input flex-1">
                <option value="">Sélectionner un service</option>
                {services.map(s => <option key={s.id} value={s.id}>{s.name || s.title}</option>)}
              </select>
              <input type="number" value={it.quantity} onChange={(e) => updateItem(idx, 'quantity', e.target.value)} className="input sm:w-24 text-center" placeholder="Qté" title="Quantité" />
              <div className="relative sm:w-32">
                <input type="number" value={it.unit_price} onChange={(e) => updateItem(idx, 'unit_price', e.target.value)} className="input w-full pr-8" placeholder="Prix" title="Prix Unitaire" />
                <span className="absolute right-3 top-3 text-md-on-surface-variant text-sm">€</span>
              </div>
            </div>
          ))}
          <div className="flex gap-3 pt-3">
            <button onClick={addItem} className="btn text-xs">
              <Plus className="size-3" /> Nouvelle ligne
            </button>
            <button onClick={createQuote} className="btn-primary flex-1">Générer le Devis</button>
          </div>
        </div>
      </div>

      <h3 className="mb-4 text-xs font-medium uppercase tracking-wider text-md-on-surface-variant">Historique récent</h3>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <AnimatePresence>
          {quotes.map((q, i) => (
            <motion.div key={q.id} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: Math.min(i * 0.05, 0.5), ease: [0.2, 0, 0, 1] }} className="list-item-glass">
              <div className="flex justify-between items-start">
                <div>
                  <div className="font-medium text-lg text-md-primary">Devis #{q.id}</div>
                  <div className="text-sm text-md-on-surface-variant">Client ID: {q.client_id}</div>
                </div>
                <div className="rounded-full bg-md-primary-container px-3 py-1 text-sm font-medium text-md-on-primary-container">
                  {q.total_amount ?? q.total} €
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </motion.section>
  );
}

/* ═══════════════════════════════════════════════════════
   INVOICES PANEL
   ═══════════════════════════════════════════════════════ */
function InvoicesPanel() {
  const token = localStorage.getItem('auth_token');
  const [invoices, setInvoices] = useState([]);
  const [quotes, setQuotes] = useState([]);
  const [quoteId, setQuoteId] = useState('');

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const [ri, rq] = await Promise.all([
          fetch(`${API_BASE_URL}/api/invoices`, { headers: { ...(token ? { Authorization: 'Bearer ' + token } : {}) } }),
          fetch(`${API_BASE_URL}/api/quotes`, { headers: { ...(token ? { Authorization: 'Bearer ' + token } : {}) } }),
        ]);
        if (ri.ok) { const ii = await ri.json(); if (mounted) setInvoices(ii || []); }
        if (rq.ok) { const qq = await rq.json(); if (mounted) setQuotes(qq || []); }
      } catch (e) { console.warn('invoices init', e.message); }
    })();
    return () => { mounted = false; };
  }, [token]);

  const createInvoice = async () => {
    if (!quoteId) return toast.error('Veuillez sélectionner un devis à facturer');
    try {
      const r = await fetch(`${API_BASE_URL}/api/invoices`, { method: 'POST', headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) }, body: JSON.stringify({ quote_id: quoteId }) });
      const d = await r.json(); if (!r.ok) throw new Error(d.error || 'Erreur');
      setInvoices((i) => [d, ...i]); setQuoteId('');
      toast.success("Facture émise avec succès !");
    } catch (e) { toast.error('Création facture échouée: ' + e.message); }
  };

  return (
    <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: [0.2, 0, 0, 1] }}>
      <h2 className="mb-6 text-2xl font-medium text-md-on-surface">Facturation</h2>
      <div className="glass-panel mb-8">
        <h3 className="mb-4 text-xs font-medium uppercase tracking-wider text-md-primary">Convertir un devis en facture</h3>
        <div className="flex flex-col sm:flex-row gap-3">
          <select value={quoteId} onChange={(e) => setQuoteId(e.target.value)} className="input flex-1">
            <option value="">Sélectionner un devis existant</option>
            {quotes.map(q => <option key={q.id} value={q.id}>Devis #{q.id} — {q.total_amount ?? q.total} €</option>)}
          </select>
          <button onClick={createInvoice} className="btn-primary">
            <Plus className="size-4" /> Émettre Facture
          </button>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <AnimatePresence>
          {invoices.map((inv, i) => (
            <motion.div key={inv.id} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: Math.min(i * 0.05, 0.5), ease: [0.2, 0, 0, 1] }} className="list-item-glass relative overflow-hidden border-l-4 border-l-md-tertiary">
              <div aria-hidden="true" className="absolute -right-6 -top-6 size-24 rounded-full bg-md-tertiary-container/30 blur-xl" />
              <div className="font-medium text-md-on-surface mb-1">Facture #{inv.id}</div>
              <div className="text-2xl font-medium tracking-tight text-md-primary">{inv.total_amount ?? inv.total} <span className="text-base text-md-primary/60">€</span></div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </motion.section>
  );
}

/* ═══════════════════════════════════════════════════════
   ASSIGNMENTS PANEL
   ═══════════════════════════════════════════════════════ */
function AssignmentsPanel() {
  const token = localStorage.getItem('auth_token');
  const [assignments, setAssignments] = useState([]);
  const [agents, setAgents] = useState([]);
  const [clients, setClients] = useState([]);
  const [agentId, setAgentId] = useState('');
  const [clientId, setClientId] = useState('');

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const [ra, rc] = await Promise.all([
          fetch(`${API_BASE_URL}/api/agents`, { headers: { ...(token ? { Authorization: 'Bearer ' + token } : {}) } }).catch(() => ({ ok: false })),
          fetch(`${API_BASE_URL}/api/clients`, { headers: { ...(token ? { Authorization: 'Bearer ' + token } : {}) } }).catch(() => ({ ok: false })),
        ]);
        if (ra && ra.ok) { const a = await ra.json(); if (mounted) setAgents(a || []); }
        if (rc && rc.ok) { const c = await rc.json(); if (mounted) setClients(c || []); }
        const rs = await fetch(`${API_BASE_URL}/api/assignments`, { headers: { ...(token ? { Authorization: 'Bearer ' + token } : {}) } }).catch(() => ({ ok: false }));
        if (rs && rs.ok) { const s = await rs.json(); if (mounted) setAssignments(s || []); }
      } catch (e) { console.warn('assignments init', e.message); }
    })();
    return () => { mounted = false; };
  }, [token]);

  const createAssignment = async () => {
    if (!agentId || !clientId) return toast.error('Veuillez sélectionner un agent et un client');
    try {
      const r = await fetch(`${API_BASE_URL}/api/assignments`, { method: 'POST', headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) }, body: JSON.stringify({ agent_id: agentId, client_id: clientId }) });
      const d = await r.json(); if (!r.ok) throw new Error(d.error || 'Erreur');
      setAssignments((a) => [d, ...a]); setAgentId(''); setClientId('');
      toast.success("Assignation réussie !");
    } catch (e) { toast.error('Assignation échouée: ' + e.message); }
  };

  return (
    <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: [0.2, 0, 0, 1] }}>
      <h2 className="mb-6 text-2xl font-medium text-md-on-surface">Assignations (Staffing)</h2>
      <div className="glass-panel mb-8">
        <h3 className="mb-4 text-xs font-medium uppercase tracking-wider text-md-primary">Nouvelle Assignation</h3>
        <div className="flex flex-col sm:flex-row gap-3">
          <select value={agentId} onChange={(e) => setAgentId(e.target.value)} className="input flex-1">
            <option value="">Sélectionner un agent</option>
            {agents.map(a => <option key={a.id} value={a.id}>{a.email}</option>)}
          </select>
          <select value={clientId} onChange={(e) => setClientId(e.target.value)} className="input flex-1">
            <option value="">Sélectionner un client</option>
            {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <button onClick={createAssignment} className="btn-primary">
            <Plus className="size-4" /> Assigner
          </button>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <AnimatePresence>
          {assignments.map((asg, i) => (
            <motion.div key={asg.id} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: Math.min(i * 0.05, 0.5), ease: [0.2, 0, 0, 1] }} className="list-item-glass">
              <div className="flex items-center justify-between border-b border-md-outline-variant/30 pb-2 mb-2">
                <span className="text-xs font-medium uppercase tracking-wider text-md-on-surface-variant">ID #{asg.id}</span>
                <span className="rounded-full bg-md-primary-container px-2.5 py-0.5 text-[10px] font-medium uppercase text-md-on-primary-container">
                  {asg.status || 'Actif'}
                </span>
              </div>
              <div className="text-sm text-md-on-surface-variant">Agent: <span className="font-medium text-md-on-surface">{asg.agent_id}</span></div>
              <div className="text-sm text-md-on-surface-variant">Client: <span className="font-medium text-md-on-surface">{asg.client_id}</span></div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </motion.section>
  );
}

/* ═══════════════════════════════════════════════════════
   SHEETS PANEL
   ═══════════════════════════════════════════════════════ */
function SheetsPanel({ spreadsheetId, user }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeSheet, setActiveSheet] = useState(null);
  const token = localStorage.getItem('auth_token');

  useEffect(() => {
    let mounted = true;
    if (!spreadsheetId) {
      setLoading(false);
      return;
    }

    (async () => {
      try {
        const r = await fetch(`${API_BASE_URL}/api/user/spreadsheet/data`, {
          headers: { ...(token ? { Authorization: 'Bearer ' + token } : {}) }
        });
        const res = await r.json();
        
        if (!r.ok) throw new Error(res.error || "Erreur de chargement des données");
        
        if (mounted) {
          setData(res.data);
          const keys = Object.keys(res.data || {});
          if (keys.length > 0) setActiveSheet(keys[0]);
          setLoading(false);
        }
      } catch (e) {
        if (mounted) {
          setError(e.message);
          setLoading(false);
        }
      }
    })();

    return () => { mounted = false; };
  }, [spreadsheetId, token]);

  if (!spreadsheetId) {
    return (
      <div className="flex flex-col items-center justify-center h-[50vh] text-md-on-surface-variant">
        <Table className="size-12 mb-4 opacity-40" />
        <h3 className="text-lg font-medium">Aucun Google Sheets</h3>
        <p className="text-sm mt-2 text-center max-w-md">
          Demandez à l'agent de créer un client, un devis ou un rendez-vous pour qu'il génère automatiquement la base de données.
        </p>
      </div>
    );
  }

  return (
    <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: [0.2, 0, 0, 1] }} className="h-[calc(100vh-120px)] flex flex-col">
      <h2 className="mb-4 text-2xl font-medium text-md-on-surface flex items-center justify-between">
        Base de Données
        <a href={`https://docs.google.com/spreadsheets/d/${spreadsheetId}/edit?authuser=${user?.email || ''}`} target="_blank" rel="noopener noreferrer" className="btn text-xs px-4 py-2">
          Ouvrir dans Google Sheets
        </a>
      </h2>

      {loading ? (
        <div className="glass-panel flex-1 flex flex-col items-center justify-center gap-3 text-md-on-surface-variant">
          <span className="grid size-10 place-items-center rounded-full bg-md-primary-container text-md-primary">
            <Sparkles className="size-5" />
          </span>
          <span className="text-sm animate-pulse">Synchronisation avec Google Sheets...</span>
        </div>
      ) : error ? (
        <div className="glass-panel flex-1 flex flex-col items-center justify-center gap-3 text-md-error">
          <p>{error}</p>
        </div>
      ) : (
        <div className="glass-panel flex-1 p-0 flex flex-col overflow-hidden">
          {/* Tab bar */}
          <div className="flex items-center gap-2 border-b border-md-outline-variant/30 bg-md-surface-container-high/50 p-2 overflow-x-auto">
            {Object.keys(data || {}).map(sheetName => (
              <button
                key={sheetName}
                onClick={() => setActiveSheet(sheetName)}
                className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-all duration-300 ease-[cubic-bezier(0.2,0,0,1)] active:scale-95 ${
                  activeSheet === sheetName 
                    ? "bg-md-secondary-container text-md-on-secondary-container" 
                    : "text-md-on-surface-variant hover:bg-md-primary/10"
                }`}
              >
                {sheetName}
              </button>
            ))}
          </div>
          
          {/* Table */}
          <div className="flex-1 overflow-auto p-4">
            {activeSheet && data[activeSheet] && data[activeSheet].length > 0 ? (
              <div className="inline-block min-w-full align-middle">
                <table className="min-w-full divide-y divide-md-outline-variant/30">
                  <thead>
                    <tr>
                      {data[activeSheet][0].map((header, idx) => (
                        <th key={idx} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-md-primary bg-md-surface-container-high/30 whitespace-nowrap">
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-md-outline-variant/20">
                    {data[activeSheet].slice(1).map((row, rowIdx) => (
                      <tr key={rowIdx} className="hover:bg-md-primary/5 transition-colors duration-200">
                        {data[activeSheet][0].map((_, colIdx) => (
                          <td key={colIdx} className="px-4 py-3 text-sm text-md-on-surface truncate max-w-[150px] sm:max-w-[250px] md:max-w-[350px]" title={row[colIdx] || ''}>
                            {row[colIdx] || ''}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-md-on-surface-variant text-sm">
                Cette feuille est vide.
              </div>
            )}
          </div>
        </div>
      )}
    </motion.section>
  );
}

/* ═══════════════════════════════════════════════════════
   MAIN DASHBOARD
   ═══════════════════════════════════════════════════════ */
export default function Dashboard({ user, onLogout }) {
  const [prompt, setPrompt] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isSidebarOpen, setSidebarOpen] = useState(false);
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [threadId, setThreadId] = useState(() => crypto.randomUUID());
  const [activeView, setActiveView] = useState('chat');
  const [spreadsheetId, setSpreadsheetId] = useState(null);
  const [conversations, setConversations] = useState([]);

  const fetchConversations = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      if (!token) return;
      const res = await fetch(`${API_BASE_URL}/api/conversations`, {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (res.ok) {
        setConversations(await res.json());
      }
    } catch (err) {
      console.error("Failed to fetch conversations:", err);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, []);

  const loadConversation = async (id) => {
    try {
      const token = localStorage.getItem('auth_token');
      if (!token) return;
      const res = await fetch(`${API_BASE_URL}/api/conversations/${id}/history`, {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (res.ok) {
        const history = await res.json();
        const loadedMessages = history.map(msg => ({
          role: msg.role,
          content: msg.content
        }));
        setMessages(loadedMessages.length > 0 ? loadedMessages : [WELCOME_MESSAGE]);
        setThreadId(id);
        setActiveView('chat');
      }
    } catch (err) {
      console.error("Failed to load conversation history:", err);
      toast.error("Impossible de charger l'historique de la discussion");
    }
  };

  useEffect(() => {
    const fetchSpreadsheetId = async () => {
      try {
        const token = localStorage.getItem('auth_token');
        if (!token) return;
        const res = await fetch(`${API_BASE_URL}/api/user/spreadsheet`, {
          headers: { 'Authorization': 'Bearer ' + token }
        });
        if (res.ok) {
          const data = await res.json();
          if (data.spreadsheet_id) {
            setSpreadsheetId(data.spreadsheet_id);
          }
        }
      } catch (err) {
        console.error("Failed to fetch spreadsheet ID:", err);
      }
    };
    fetchSpreadsheetId();
  }, []);
  
  const scrollRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, isTyping]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  }, [prompt]);

  const appendResult = (data, fallbackMessages) => {
    if (data.status === "completed") {
      setMessages([...fallbackMessages, { role: "agent", content: data.response }]);
      return;
    }
    if (data.status === "waiting_approval") {
      setMessages([
        ...fallbackMessages,
        {
          role: "agent",
          content: "Votre validation est requise avant de poursuivre.",
          approval: {
            execution_id: data.execution_id,
            step_id: data.step,
            tool: data.tool,
            arguments: data.arguments,
          },
        },
      ]);
      return;
    }
    setMessages([
      ...fallbackMessages,
      { role: "agent", content: `Je n'ai pas pu terminer cette action.\n\n> ${data.error || data.message || "Erreur inconnue"}` },
    ]);
  };

  const requestApi = async (path, payload) => {
    const token = localStorage.getItem('auth_token');

    const headers = { "Content-Type": "application/json" };
    if (token) headers['Authorization'] = 'Bearer ' + token;

    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });

    if (response.status === 401) {
      onLogout();
      throw new Error("Session expirée. Veuillez vous reconnecter.");
    }

    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `Erreur serveur (${response.status})`);
    return data;
  };

  const handleApprove = async (approval, approved) => {
    setMessages((current) =>
      current.map((message) =>
        message.approval?.execution_id === approval.execution_id
          ? {
              ...message,
              approval: null,
              content: `${message.content}\n\n> Action ${approved ? "approuvée" : "refusée"}.`,
            }
          : message,
      ),
    );
    setIsTyping(true);
    try {
      const data = await requestApi("/api/approve", { ...approval, approved, thread_id: threadId });
      setMessages((current) => {
        if (data.status === "completed") return [...current, { role: "agent", content: data.response }];
        if (data.status === "waiting_approval") {
          return [...current, {
            role: "agent",
            content: "Une autre validation est requise pour continuer.",
            approval: { execution_id: data.execution_id, step_id: data.step, tool: data.tool, arguments: data.arguments },
          }];
        }
        return [...current, { role: "agent", content: `> ${data.error || data.message || "Action non terminée"}` }];
      });
    } catch (error) {
      setMessages((current) => [...current, { role: "agent", content: `> Erreur de connexion : ${error.message}` }]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSend = async (suggestion) => {
    const text = (suggestion ?? prompt).trim();
    if (!text || isTyping) return;
    const nextMessages = [...messages, { role: "user", content: text }];
    setMessages(nextMessages);
    setPrompt("");
    setIsTyping(true);
    try {
      appendResult(await requestApi("/api/chat", { prompt: text, thread_id: threadId }), nextMessages);
    } catch (error) {
      setMessages([...nextMessages, { role: "agent", content: `Erreur: ${error.message}` }]);
    } finally {
      setIsTyping(false);
      // Refresh the conversations list to update the title if it's a new conversation
      fetchConversations();
    }
  };

  const startNewChat = () => {
    setMessages([WELCOME_MESSAGE]);
    setPrompt("");
    setThreadId(crypto.randomUUID());
    setSidebarOpen(false);
    textareaRef.current?.focus();
    setActiveView('chat');
  };

  return (
    <main className="flex h-[100dvh] overflow-hidden bg-md-background text-md-on-surface">
      <Toaster richColors />      {/* Mobile Backdrop */}
      {isSidebarOpen && (
        <div className="fixed inset-0 z-30 bg-black/40 backdrop-blur-sm transition-opacity md:hidden" onClick={() => setSidebarOpen(false)} />
      )}
      <Sidebar 
        open={isSidebarOpen} 
        onClose={() => setSidebarOpen(false)} 
        onNewChat={startNewChat} 
        user={user} 
        onLogout={onLogout} 
        setView={setActiveView} 
        spreadsheetId={spreadsheetId}
        conversations={conversations}
        activeThreadId={threadId}
        onSelectConversation={loadConversation}
      />

      <section className="relative flex min-w-0 flex-1 flex-col">
        {/* ── Header ── */}
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-md-outline-variant/30 bg-md-surface/80 backdrop-blur-md px-3 md:px-5">
          <div className="flex items-center gap-2">
            <button onClick={() => setSidebarOpen(true)} className="icon-button md:hidden" aria-label="Ouvrir le menu">
              <Menu className="size-5" />
            </button>
            <button className="flex items-center gap-1.5 rounded-full px-3 py-2 text-sm font-medium text-md-on-surface hover:bg-md-primary/10 transition-all duration-200 active:scale-95">
              Commercial AI <ChevronDown className="size-4 text-md-on-surface-variant" />
            </button>
          </div>
          <div className="flex items-center gap-1">
            <button className="icon-button hidden sm:grid" aria-label="Rechercher"><Search className="size-[18px]" /></button>
            <button className="icon-button hidden sm:grid" aria-label="Compte"><UserRound className="size-[18px]" /></button>
            <button onClick={startNewChat} className="icon-button md:hidden" aria-label="Nouvelle discussion"><Plus className="size-5" /></button>
          </div>
        </header>

        {/* ── Content Area ── */}
        <div ref={scrollRef} className="chat-scroll flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-3xl px-4 pb-44 pt-5 sm:px-6 sm:pt-8">
            {activeView === 'chat' ? (
              <>
                {messages.map((message, index) => (
                  <ChatMessage key={`${message.role}-${index}`} message={message} onApprove={handleApprove} />
                ))}

                {messages.length === 1 && !isTyping && (
                  <div className="mt-7 grid gap-3 sm:grid-cols-3">
                    {SUGGESTIONS.map((suggestion) => (
                      <button key={suggestion} onClick={() => handleSend(suggestion)} className="suggestion-card">
                        <span>{suggestion}</span>
                        <ArrowUp className="size-4 shrink-0 text-md-primary" />
                      </button>
                    ))}
                  </div>
                )}

                {isTyping && (
                  <div className="flex items-center gap-3 py-5 text-sm text-md-on-surface-variant">
                    <span className="grid size-7 place-items-center rounded-full bg-md-primary text-white"><Sparkles className="size-3.5" /></span>
                    <span className="thinking-dots"><i /><i /><i /></span>
                  </div>
                )}
              </>
            ) : (
              <div>
                {activeView === 'clients' && <ClientsPanel />}
                {activeView === 'services' && <ServicesPanel />}
                {activeView === 'quotes' && <QuotesPanel />}
                {activeView === 'invoices' && <InvoicesPanel />}
                {activeView === 'assignments' && <AssignmentsPanel />}
                {activeView === 'sheets' && <SheetsPanel spreadsheetId={spreadsheetId} user={user} />}
              </div>
            )}
          </div>
        </div>

        {/* ── Chat Composer ── */}
        {activeView === 'chat' ? (
          <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-md-background via-md-background/90 to-transparent px-3 pb-3 pt-12 sm:px-6 sm:pb-5">
            <div className="pointer-events-auto mx-auto max-w-3xl">
              <div className="composer-shell">
                <button className="icon-button mb-0.5 shrink-0" aria-label="Joindre un fichier" title="Les pièces jointes seront bientôt disponibles">
                  <Paperclip className="size-[19px]" />
                </button>
                <textarea
                  ref={textareaRef}
                  value={prompt}
                  onChange={(event) => setPrompt(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder="Message Commercial AI"
                  rows="1"
                  className="min-h-11 max-h-[200px] flex-1 resize-none bg-transparent py-3 text-[15px] leading-6 text-md-on-surface outline-none placeholder:text-md-on-surface-variant/50"
                />
                <button onClick={() => handleSend()} disabled={!prompt.trim() || isTyping} className="send-button" aria-label="Envoyer le message">
                  <ArrowUp className="size-[19px] stroke-[2.5]" />
                </button>
              </div>
              <p className="mt-2 text-center text-[11px] text-md-on-surface-variant/60">Commercial AI peut faire des erreurs. Vérifiez les devis avant envoi.</p>
            </div>
          </div>
        ) : null}
      </section>
    </main>
  );
}
