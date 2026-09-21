# 🤖 Commercial AI Agent

> **Assistant commercial intelligent** qui automatise la création de devis, la gestion des clients, l'envoi d'e-mails et la planification de réunions — le tout via une interface conversationnelle en langage naturel.

[![Deployed on Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-black?logo=vercel)](https://agent.yahya.ink)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://reactjs.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask)](https://flask.palletsprojects.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.0+-green)](https://langchain-ai.github.io/langgraph/)

**🌐 Production :** [https://agent.yahya.ink](https://agent.yahya.ink)

---

## 📋 Table des Matières

- [Vue d'ensemble](#-vue-densemble)
- [Architecture](#-architecture)
- [Backend](#-backend)
  - [API REST](#api-rest)
  - [Agents IA](#agents-ia)
  - [Outils MCP](#outils-mcp)
  - [Base de données](#base-de-données)
- [Frontend](#-frontend)
- [Variables d'environnement](#-variables-denvironnement)
- [Installation locale](#-installation-locale)
- [Déploiement Vercel](#-déploiement-vercel)
- [Flux de travail](#-flux-de-travail)

---

## 🌟 Vue d'ensemble

Commercial AI Agent est une application full-stack qui permet à une agence web ou digitale de gérer ses opérations commerciales via une interface de chat alimentée par l'IA. L'utilisateur s'authentifie avec Google, puis interagit avec un agent en langage naturel (français ou autre) pour :

| Action | Exemple de commande |
|--------|---------------------|
| 💼 Créer un devis | *"Crée un devis pour Atlas Group : site e-commerce + SEO 6 mois"* |
| 📄 Générer un PDF | *"Génère le PDF du devis et envoie-le à client@example.com"* |
| 👤 Gérer les clients | *"Ajoute le client Dupont avec email jean@dupont.ma"* |
| 📅 Planifier une réunion | *"Réserve un meeting vendredi 15h avec ahmed@gmail.com"* |
| 💰 Mettre à jour les prix | *"Change le prix de WEB-ECOMM à 25000 MAD"* |
| 📊 Consulter le catalogue | *"Quels sont nos services pour la création de site web ?"* |
| 📬 Envoyer des emails | *"Envoie le devis par email au client"* |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          VERCEL (Production)                        │
│                                                                     │
│   ┌─────────────────────┐      ┌───────────────────────────────┐   │
│   │   FRONTEND (React)  │      │        BACKEND (Flask)        │   │
│   │                     │      │                               │   │
│   │  ┌───────────────┐  │ REST │  ┌─────────────────────────┐ │   │
│   │  │  Dashboard    │◄─┼──────┼─►│     API Routes          │ │   │
│   │  │  (Chat UI)    │  │      │  │  /api/approve           │ │   │
│   │  └───────────────┘  │      │  │  /api/auth/google       │ │   │
│   │                     │      │  │  /api/clients           │ │   │
│   │  ┌───────────────┐  │      │  │  /api/quotes            │ │   │
│   │  │  ClientsPanel │  │      │  │  /api/services          │ │   │
│   │  │  (CRM View)   │  │      │  └──────────────┬──────────┘ │   │
│   │  └───────────────┘  │      │                 │            │   │
│   └─────────────────────┘      │  ┌──────────────▼──────────┐ │   │
│                                │  │  LangGraph Orchestrator  │ │   │
│                                │  │  ┌────────────────────┐  │ │   │
│                                │  │  │ PromptEngineerAgent │  │ │   │
│                                │  │  │ PlannerAgent        │  │ │   │
│                                │  │  │ ExecutionEngine     │  │ │   │
│                                │  │  │ ResponseAgent       │  │ │   │
│                                │  │  └────────────────────┘  │ │   │
│                                │  └──────────────┬──────────┘ │   │
│                                │                 │            │   │
│                                │  ┌──────────────▼──────────┐ │   │
│                                │  │      MCP Tools (16)      │ │   │
│                                │  │  db.* | doc.* | email.*  │ │   │
│                                │  │  calendar.* | sheets.*   │ │   │
│                                │  └──────────────┬──────────┘ │   │
│                                └─────────────────┼────────────┘   │
└─────────────────────────────────────────────────┼─────────────────┘
                                                  │
                    ┌─────────────────────────────▼──────────────────┐
                    │             SERVICES EXTERNES                   │
                    │  ┌──────────┐  ┌──────────┐  ┌─────────────┐  │
                    │  │  Groq AI │  │ Google   │  │  PostgreSQL │  │
                    │  │  (LLM)   │  │ Workspace│  │  (Neon.io)  │  │
                    │  └──────────┘  └──────────┘  └─────────────┘  │
                    └────────────────────────────────────────────────┘
```

---

## 🐍 Backend

**Technologie :** Python 3.11, Flask 3.0, SQLAlchemy 2.0, LangGraph 1.0

### Structure des dossiers

```
backend/
├── agents/                    # Agents IA (cerveau de l'application)
│   ├── langgraph_orchestrator.py  # Orchestre le flux de travail IA
│   ├── prompt_engineer.py     # Traduit le langage naturel en JSON d'intent
│   ├── planner.py             # Planifie les étapes d'exécution
│   └── response_agent.py      # Génère la réponse finale en langage naturel
│
├── api/                       # API REST Flask
│   ├── app.py                 # Factory Flask + CORS + blueprints
│   ├── auth.py                # OAuth Google + JWT
│   ├── chat.py                # Endpoint /api/approve (conversation)
│   ├── dashboard.py           # CRUD clients/devis/factures
│   └── middleware.py          # Logging, correlation IDs
│
├── mcp/                       # Model Context Protocol Tools
│   ├── database/              # Outils base de données (6 outils)
│   ├── document/              # Génération PDF/Excel (2 outils)
│   ├── email/                 # Envoi d'emails Gmail (2 outils)
│   ├── google_calendar/       # Google Calendar (2 outils)
│   ├── google_sheets/         # Google Sheets (3 outils)
│   └── registry.py            # Registre central de tous les outils
│
├── models/                    # Modèles SQLAlchemy
│   ├── client.py              # Client (nom, email, téléphone, adresse)
│   ├── quote.py               # Devis + QuoteItem (ligne de devis)
│   ├── invoice.py             # Facture + InvoiceItem
│   ├── service.py             # Service/Produit du catalogue
│   ├── user.py                # Utilisateur (auth Google)
│   ├── assignment.py          # Assignation mission-client
│   ├── document.py            # Document généré (PDF, XLSX)
│   └── execution.py           # Historique d'exécution des agents
│
├── llm/
│   └── router.py              # Routeur LLM (Groq / Ollama)
│
├── config/
│   └── settings.py            # Configuration centralisée (Pydantic)
│
├── execution/
│   ├── executor_improved.py   # Moteur d'exécution des outils MCP
│   └── state_machine.py       # Machine à états pour l'exécution
│
└── security/                  # JWT, validation, rate limiting
```

---

### API REST

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/api/auth/google` | Échange le code OAuth Google contre un JWT |
| `GET` | `/api/auth/google/config` | Retourne le `client_id` Google pour le frontend |
| `POST` | `/api/login` | Connexion email/mot de passe |
| `POST` | `/api/approve` | **Point d'entrée principal** — envoie un message à l'agent |
| `GET` | `/api/clients` | Liste tous les clients |
| `POST` | `/api/clients` | Crée un nouveau client |
| `GET` | `/api/quotes` | Liste tous les devis (avec items) |
| `GET` | `/api/invoices` | Liste toutes les factures (avec items) |
| `GET` | `/api/services` | Liste le catalogue de services |
| `PUT` | `/api/services/<id>` | Met à jour un service (prix, description) |
| `GET` | `/api/user/spreadsheet/data` | Données du Google Sheets lié |
| `GET` | `/health` | Health check |

---

### Agents IA

Le flux conversationnel suit un **graphe LangGraph** avec 4 nœuds :

```
User Input
    │
    ▼
[1] PromptEngineerAgent
    │  Analyse le texte en langage naturel
    │  Extrait : intent, client, services, actions[], remise, TVA
    │  Règle critique : questions informatives → actions:[] (pas de document créé)
    │
    ▼
[2] PlannerAgent
    │  Transforme l'intent en plan d'exécution séquentiel
    │  Identifie les étapes nécessitant une approbation humaine
    │
    ▼
[3] ExecutionEngine
    │  Exécute chaque étape du plan (outils MCP)
    │  Si approbation requise → suspend et retourne au frontend
    │  Si approuvé → continue l'exécution
    │
    ▼
[4] ResponseAgent
    │  Génère une réponse en langage naturel depuis les résultats
    │
    ▼
Réponse finale
```

**Checkpointing :** LangGraph sauvegarde l'état de chaque conversation dans PostgreSQL (production) ou SQLite (développement), permettant de reprendre une conversation après une pause d'approbation.

---

### Outils MCP

L'application utilise le protocole **MCP (Model Context Protocol)** pour structurer les capacités de l'agent en outils réutilisables. Il y a **16 outils** répartis en 5 catégories :

#### 🗄️ Outils Base de Données (6 outils)
| Outil | Description | Approbation |
|-------|-------------|-------------|
| `db.search_client` | Recherche un client par nom | ❌ |
| `db.find_or_create_client` | Trouve ou crée automatiquement un client ⭐ | ❌ |
| `db.create_client` | Crée un nouveau client | ❌ |
| `db.get_services` | Récupère le catalogue des services | ❌ |
| `db.create_quote` | Crée un devis avec lignes d'articles | ❌ |
| `db.get_quote` | Récupère les détails d'un devis | ❌ |
| `db.create_service` | Ajoute un service au catalogue (avec prix) | ❌ |
| `db.update_service_price` | Met à jour le prix d'un service existant | ❌ |

#### 📄 Outils Document (2 outils)
| Outil | Description | Approbation |
|-------|-------------|-------------|
| `document.generate` | Génère un PDF professionnel (LaTeX) | ✅ |
| `document.generate_excel` | Génère un devis Excel (XLSX) | ✅ |

#### 📬 Outils Email (2 outils)
| Outil | Description | Approbation |
|-------|-------------|-------------|
| `email.prepare` | Prépare le brouillon de l'email | ❌ |
| `email.send` | Envoie l'email via l'API Gmail | ✅ |

#### 📅 Google Calendar (2 outils)
| Outil | Description | Approbation |
|-------|-------------|-------------|
| `google.calendar.check_availability` | Vérifie les disponibilités | ❌ |
| `google.calendar.create_meeting` | Crée un événement Google Calendar | ✅ |

#### 📊 Google Sheets (3 outils)
| Outil | Description | Approbation |
|-------|-------------|-------------|
| `google.sheets.append_row` | Ajoute une ligne dans le Sheets CRM | ✅ |
| `google.sheets.get_data` | Récupère les données du Sheets | ❌ |
| `google.sheets.create_spreadsheet` | Crée un nouveau Google Sheets | ✅ |

> **Note sur les approbations :** Les actions à ✅ nécessitent une confirmation explicite de l'utilisateur dans l'interface avant d'être exécutées. C'est une mesure de sécurité qui garantit que l'agent n'envoie jamais d'emails ou ne crée jamais de fichiers sans votre accord.

---

### Base de Données

**Production :** PostgreSQL (Neon.io)  
**Développement :** SQLite

#### Schéma principal

```
users
 ├── id, email, google_id, access_token, refresh_token
 └── spreadsheet_id (lien vers le Google Sheets CRM)

clients
 ├── id, name, email, phone, address, company
 └── created_at, user_id (FK)

services (Catalogue)
 ├── id, code (ex: WEB-SHOW), name, description
 ├── unit_price, currency (MAD)
 └── category, is_active

quotes
 ├── id, client_id (FK), status, total_ht, total_ttc
 ├── discount_percent, tax_rate, validity_days
 └── QuoteItem: service_id, quantity, unit_price, discount

invoices
 ├── id, client_id (FK), quote_id (FK)
 └── InvoiceItem: service_id, quantity, unit_price, discount

assignments
 └── id, client_id (FK), title, description, status
```

---

#### Catalogue de Services (seed initial)
| Code | Service | Prix (MAD) |
|------|---------|-----------|
| `WEB-SHOW` | Site vitrine | 5 000 |
| `WEB-ECOMM` | Site e-commerce | 15 000 |
| `APP-MOB` | Application mobile | 35 000 |
| `UI-UX` | Design UI/UX | 8 000 |
| `SEO-OPT` | Optimisation SEO | 3 000 |
| `MAINT-12` | Maintenance annuelle | 6 000 |
| `HOST-12` | Hébergement annuel | 2 000 |
| `MGT-COMM` | Gestion réseaux sociaux | 2 000 |
| `CONSULT` | Consultation/Audit | 1 500 |
| `AUDIT-IT` | Audit technique complet | 4 000 |

---

## ⚛️ Frontend

**Technologie :** React 19, Vite 8, TailwindCSS v4, Framer Motion, Lucide Icons

### Structure

```
frontend/src/
├── pages/
│   ├── Dashboard.jsx       # Interface principale (chat + panneaux CRM)
│   ├── Login.jsx           # Page de connexion (Google OAuth + email/MDP)
│   ├── Privacy.jsx         # Politique de confidentialité (Google OAuth requis)
│   └── Terms.jsx           # Conditions d'utilisation
│
├── components/
│   └── ui/
│       └── ChatMessage.jsx # Bulle de message (agent / utilisateur)
│
├── index.css               # Système de design (thème sombre premium)
├── App.jsx                 # Routage SPA simple (/, /privacy, /terms)
└── main.jsx                # Entrée + GoogleOAuthProvider
```

### Système de Design

Le design utilise un thème **sombre premium** inspiré des meilleurs SaaS (Linear, Vercel, Raycast) :

- **Couleurs :** Fond `#080B14`, accents **Violet → Indigo → Cyan**
- **Typographie :** Police **Inter** (300 → 800)
- **Effets :** Glassmorphisme, orbes animées, glows colorés
- **Animations :** Framer Motion pour toutes les transitions de page et de composant

### Composants Principaux

#### Dashboard (interface principale)
- **Sidebar** : Navigation colorée par module, historique des conversations, profil utilisateur
- **Zone de chat** : Messages markdown riches, bulles agent/utilisateur, système d'approbation intégré
- **Suggestion cards** : Suggestions de commandes pour guider l'utilisateur débutant

#### Panel Clients (CRM Master-Detail)
- **Liste** (gauche) : Clients avec avatar, nom, email
- **Détail** (droite) : Sélectionnez un client pour voir ses réunions (depuis Google Sheets), devis (avec toutes les lignes d'articles, remises, TVA) et factures

#### Système d'Approbation
Quand l'agent veut effectuer une action irréversible (envoyer un email, créer un PDF, écrire dans Sheets), il suspende l'exécution et affiche une **Approval Card** dans le chat. L'utilisateur peut :
- ✅ **Approuver** → l'action s'exécute
- ❌ **Rejeter** → l'action est annulée

---

## ⚙️ Variables d'Environnement

Copiez `.env.example` vers `.env` et remplissez :

```env
# ── Environnement ──
APP_ENV=production
FRONTEND_URL=https://agent.yahya.ink

# ── Base de Données ──
DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname

# ── LLM Provider ──
LLM_PROVIDER=groq                    # "groq" (production) ou "ollama" (local)
GROQ_API_KEY=gsk_...                 # Clé API Groq
GROQ_MODEL=qwen/qwen3.8-27b         # Modèle principal
GROQ_FAST_MODEL=qwen/qwen3.8-27b   # Modèle rapide

# ── Google OAuth ──
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...

# ── Sécurité ──
JWT_SECRET=un_secret_aleatoire_de_32_caracteres_minimum

# ── CORS ──
CORS_ORIGINS=https://agent.yahya.ink
```

---

## 🚀 Installation Locale

### Prérequis
- Python 3.11+
- Node.js 20+
- PostgreSQL (ou utiliser SQLite pour le dev)

### 1. Backend

```bash
git clone https://github.com/Bouchask/assitance-ai.git
cd assitance-ai/commercial-ai-agent

# Créer l'environnement virtuel
python -m venv .venv
source .venv/bin/activate   # Windows : .venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Configurer l'environnement
cp .env.example .env
# → Éditez .env avec vos clés

# Créer les tables en base de données
python -c "from backend.database.session import Base, engine; from backend.models import *; Base.metadata.create_all(engine)"

# Lancer le serveur de développement
python backend/run.py
# → API disponible sur http://localhost:5000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
# → Interface disponible sur http://localhost:5175
```

### 3. LLM Local (optionnel, sans Groq)

```bash
# Installer Ollama : https://ollama.com
ollama pull gemma4:12b-mlx

# Dans .env : LLM_PROVIDER=ollama
```

---

## ☁️ Déploiement Vercel

Le projet est configuré pour Vercel via `vercel.json` avec :
- **Backend Flask** → fonction Python serverless (`api/index.py`)
- **Frontend React** → build statique Vite

```bash
# Première fois
npm i -g vercel
vercel login
vercel link

# Déployer en production
vercel --prod --yes
```

### Variables à configurer sur Vercel Dashboard

Allez dans **Settings → Environment Variables** de votre projet Vercel et ajoutez toutes les variables de la section ci-dessus.

---

## 🔄 Flux de Travail Complet

### Exemple : Créer et envoyer un devis

```
Utilisateur : "Crée un devis pour Atlas E-Commerce avec site e-commerce 15000 MAD 
               et SEO 3 mois à 9000 MAD, remise 10%, envoie-le par email"

[PromptEngineer] → intent = {
    client: "Atlas E-Commerce",
    items: [
        {code: "WEB-ECOMM", qty: 1, price: 15000},
        {code: "SEO-OPT",   qty: 3, price: 3000}
    ],
    discount: 10,
    tax_rate: 20,
    actions: [
        "db.find_or_create_client",
        "utils.prepare_quote_items",
        "db.create_quote",
        "document.generate",     ← ✅ Approbation requise
        "email.prepare",
        "email.send"             ← ✅ Approbation requise
    ]
}

[PlannerAgent] → 6 étapes planifiées

[ExecutionEngine] :
  ✅ Étape 1 : Trouve "Atlas E-Commerce" dans la DB → id: 42
  ✅ Étape 2 : Prépare les items → total HT: 27000 MAD → remise 10% → 24300 MAD
  ✅ Étape 3 : Crée le devis en base → quote_id: 156

  ⏸️ Étape 4 : "Générer PDF ?" → APPROBATION USER
  [User clique Approuver]
  ✅ PDF généré → /tmp/devis_atlas_156.pdf

  ⏸️ Étape 5 : "Envoyer à contact@atlas.ma ?" → APPROBATION USER
  [User clique Approuver]
  ✅ Email envoyé via Gmail API

[ResponseAgent] : "Le devis n°156 pour Atlas E-Commerce a été créé 
                   (24 300 MAD HT, 29 160 MAD TTC) et envoyé avec succès 
                   à contact@atlas.ma ! 📨"
```

---

## 🛡️ Sécurité

- **Authentification :** Google OAuth 2.0 + JWT (HS256, secret ≥ 32 caractères)
- **Autorisations :** Chaque action destructive nécessite une approbation explicite de l'utilisateur
- **CORS :** Restreint au domaine de production
- **Rate Limiting :** Flask-Limiter sur les endpoints sensibles
- **Tokens Google :** Stockés en base (chiffrés en transit via HTTPS)

---

## 📦 Stack Technique Complète

| Couche | Technologie | Version |
|--------|-------------|---------|
| Frontend | React + Vite | 19 / 8.x |
| Styling | TailwindCSS v4 + Framer Motion | 4.x |
| Backend | Flask | 3.0+ |
| ORM | SQLAlchemy + Alembic | 2.0 |
| Base de Données (prod) | PostgreSQL (Neon) | 16 |
| Orchestration IA | LangGraph | 1.0+ |
| LLM (prod) | Groq API (Qwen 3) | - |
| LLM (local) | Ollama (Gemma/Qwen) | - |
| Auth | Google OAuth 2.0 + JWT | - |
| Documents | LaTeX (pdflatex) + OpenPyXL | - |
| Emails | Google Gmail API | v1 |
| Agenda | Google Calendar API | v3 |
| CRM Log | Google Sheets API | v4 |
| Hosting | Vercel | - |

---

## 📞 Support

Pour toute question ou problème, contactez : **bouchakyahya0@gmail.com**

- [Politique de Confidentialité](https://agent.yahya.ink/privacy)
- [Conditions d'Utilisation](https://agent.yahya.ink/terms)
