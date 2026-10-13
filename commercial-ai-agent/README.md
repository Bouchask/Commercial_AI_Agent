# 🤖 Commercial AI Agent

> **Assistant commercial intelligent** pour gérer les opérations d'une agence depuis une interface conversationnelle : CRM, devis, documents, e-mails et réunions.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask)](https://flask.palletsprojects.com)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-1C3C3C)](https://langchain-ai.github.io/langgraph/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Deployment](https://img.shields.io/badge/Deployment-Vercel-black?logo=vercel)](https://vercel.com)

**Application :** [agent.yahya.ink](https://agent.yahya.ink) · **Repository :** [Bouchask/Commercial_AI_Agent](https://github.com/Bouchask/Commercial_AI_Agent)

> **Project status:** This README describes the intended architecture and documented capabilities. It is not a guarantee that every integration is configured or every workflow has been verified in production. See [Known limitations and hardening priorities](#-known-limitations-and-hardening-priorities).

---

## Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Technology stack](#-technology-stack)
- [Repository structure](#-repository-structure)
- [Workflow lifecycle](#-workflow-lifecycle)
- [Integrations and tools](#-integrations-and-tools)
- [Data model](#-data-model)
- [Local development](#-local-development)
- [Environment configuration](#-environment-configuration)
- [Deployment](#-deployment)
- [Security model](#-security-model)
- [Testing](#-testing)
- [Known limitations and hardening priorities](#-known-limitations-and-hardening-priorities)
- [Roadmap](#-roadmap)

## 🌟 Overview

Commercial AI Agent is a full-stack AI-assisted commercial operations application designed for digital agencies and small businesses. Users can express requests in natural language, while a backend workflow interprets the request, creates a plan, and calls registered tools to perform supported business actions.

The project combines a conversational interface with CRM and document workflows. LangGraph coordinates the workflow; Flask exposes the API; SQLAlchemy provides database access; and integrations connect the application to selected Google Workspace services and an LLM provider.

### Example requests

- “Show me the services available for an e-commerce website.”
- “Prepare a quote for a website and three months of SEO.”
- “Create a PDF version of this quote.”
- “Check availability and schedule a meeting with this client.”
- “Draft an email with the generated document attached.”

Examples describe intended usage. Actual results depend on database contents, configured credentials, enabled tools and successful execution.

## ✨ Features

| Area | Capability |
|---|---|
| Conversational interface | Submit commercial requests in natural language and receive a summarized result |
| AI workflow | Extract intent, plan dependent steps, execute tools and compose a response |
| CRM | Manage clients and service catalogue data through backend API routes |
| Quotes and invoices | Create and review commercial records and line items |
| Document generation | Generate PDF and spreadsheet documents using registered document tools |
| Email | Prepare messages and, when configured and authorized, send them through an email provider |
| Calendar | Check availability and create meetings through Google Calendar integration |
| Spreadsheet logging | Read or append CRM-related data through Google Sheets tools |
| Human approval | Pause selected high-impact tool calls for user review |
| Persistence | Store application records in SQLAlchemy-supported databases and checkpoint workflow state when configured |

## 🏗️ Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                    React + Vite frontend                     │
│          Chat · CRM views · Quote/invoice views               │
└──────────────────────────────┬───────────────────────────────┘
                               │ HTTPS / REST
┌──────────────────────────────▼───────────────────────────────┐
│                       Flask API                              │
│     Authentication · Validation · Business endpoints         │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                  LangGraph orchestrator                      │
│  Intent analysis → Planning → Execution → Response            │
│                 ↘ Approval / resume ↗                        │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                    Registered tool layer                     │
│  Database · Documents · Email · Calendar · Google Sheets      │
└──────────────┬────────────────┬────────────────┬─────────────┘
               │                │                │
          PostgreSQL/       LLM provider     Google APIs
          SQLite (dev)    (configured model)  (OAuth scopes)
```

### Design principles

- **Explicit tool boundaries:** the model proposes actions; registered backend handlers perform them.
- **Dependency-aware plans:** later steps can consume results from earlier steps.
- **Human oversight:** selected actions can pause for approval before execution.
- **Persistent state:** database records and LangGraph checkpoints support conversation and workflow continuity when configured.
- **Separation of concerns:** UI, API, orchestration, tools, models and configuration are organized into distinct modules.

These principles describe the intended design. Approval enforcement, authorization, persistence and retry behavior must still be tested against the deployed configuration.

## 🧰 Technology stack

| Layer | Technologies |
|---|---|
| Frontend | React, Vite, Tailwind CSS, Framer Motion |
| Backend API | Python 3.11+, Flask |
| ORM and models | SQLAlchemy |
| AI orchestration | LangGraph |
| Model access | LLM router with provider configuration; Groq and Ollama are represented in the project |
| Persistence | PostgreSQL in production configuration; SQLite for local development/testing |
| Identity | Google OAuth and JWT-based API authentication |
| Integrations | Gmail, Google Calendar and Google Sheets APIs |
| Documents | PDF generation and Excel/XLSX generation |
| Deployment | Vercel configuration and GitHub Actions workflow |

Exact dependency versions should be taken from the repository's lockfiles and requirements files, not inferred from these technology labels.

## 📁 Repository structure

The application implementation is primarily under `commercial-ai-agent/`.

```text
commercial-ai-agent/
├── api/
│   └── index.py                  # Serverless entry point
├── backend/
│   ├── agents/
│   │   ├── langgraph_orchestrator.py
│   │   ├── prompt_engineer.py
│   │   ├── planner.py
│   │   └── response_agent.py
│   ├── api/
│   │   ├── app.py                # Flask application factory and routes
│   │   ├── auth.py               # Authentication routes/helpers
│   │   ├── chat.py               # Conversation/approval workflow
│   │   └── dashboard.py          # CRM and commercial API routes
│   ├── config/                   # Application settings
│   ├── database/                 # SQLAlchemy connection/session setup
│   ├── execution/
│   │   ├── executor_improved.py  # Tool execution engine
│   │   ├── approval.py           # Approval policy helper
│   │   └── state_machine.py      # Execution states
│   ├── llm/                      # Model routing
│   ├── mcp/
│   │   ├── database/
│   │   ├── document/
│   │   ├── email/
│   │   ├── google_calendar/
│   │   ├── google_sheets/
│   │   └── registry.py           # Registered tools
│   ├── models/                   # SQLAlchemy models
│   └── tests/unit/               # Unit tests
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   └── pages/
│   ├── package.json
│   └── vite.config.*
├── requirements.txt
├── vercel.json
└── .env.example
```

The repository also contains a root-level frontend directory. Confirm which frontend is intended for each deployment before making structural changes; the configured Vercel project should be treated as the source of truth for the deployed build.

## 🔄 Workflow lifecycle

A typical request follows this sequence:

1. **Receive request:** the API associates the request with the authenticated user and conversation.
2. **Analyze intent:** the prompt-analysis agent extracts the goal, entities, parameters and requested actions.
3. **Plan:** the planner proposes a sequence of registered tools and dependencies.
4. **Validate:** tool names, arguments, dependencies and authorization should be checked before execution.
5. **Execute:** the engine invokes eligible tools and records results.
6. **Request approval:** selected actions pause so the user can review the proposed operation.
7. **Resume:** the workflow continues after an approval decision, where supported.
8. **Report:** the response agent summarizes the actual recorded outcomes.

### Important execution rule

An LLM-generated plan is untrusted input. It must not be treated as authorization. The backend must independently validate tool arguments, enforce user ownership and require an explicit successful approval for actions that need one. An approval-check error must stop execution, not allow it to continue.

## 🔌 Integrations and tools

Tools are registered through the project's tool registry. Availability depends on the registered handler, credentials, environment variables, database state and provider permissions.

| Category | Examples | Typical use |
|---|---|---|
| Database | Client, service and quote handlers | Search or modify business records |
| Documents | PDF and Excel generation | Produce commercial documents |
| Email | Prepare and send | Draft or deliver messages |
| Calendar | Availability and meeting creation | Coordinate meetings |
| Google Sheets | Read, append and create spreadsheet operations | Synchronize or log commercial data |

For email, the system must distinguish a real provider-confirmed send from a simulated or failed attempt. A simulated result must never be reported as a delivered email or used to mark a quote as sent.

## 🗃️ Data model

The SQLAlchemy models cover application entities such as:

- **Users:** authenticated accounts and integration configuration.
- **Clients:** customer details and ownership associations.
- **Services:** catalogue codes, descriptions and prices.
- **Quotes and quote items:** commercial offers and line items.
- **Invoices and invoice items:** billing records.
- **Documents:** generated-file metadata and, where configured, stored content.
- **Executions and messages:** workflow state and conversation history.
- **Assignments:** client or work assignments where enabled.

The exact schema can change with migrations. Production schema changes should be applied through a controlled migration process rather than ad hoc changes during application startup.

## 💻 Local development

### Prerequisites

- Python 3.11 or a compatible version supported by the project dependencies.
- Node.js and npm versions compatible with the frontend lockfile.
- Git.
- PostgreSQL for a PostgreSQL-based local setup, or SQLite if supported by the current configuration.
- API credentials only for the external integrations you want to test.

### 1. Clone and enter the application

```bash
git clone https://github.com/Bouchask/Commercial_AI_Agent.git
cd Commercial_AI_Agent/commercial-ai-agent
```

### 2. Set up the backend

```bash
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set the required configuration. Do not commit real credentials or production secrets.

Start the backend using the entry point documented by the current repository configuration. Check the available run scripts before assuming a particular port:

```bash
python backend/run.py
```

If this entry point is absent or differs in your checkout, use the current run script or Flask application factory defined by the repository.

### 3. Set up the frontend

```bash
cd frontend
npm ci
npm run dev
```

Use the local URL printed by Vite. Configure the frontend API base URL or development proxy to point to the backend.

### 4. Run tests

From the application directory, activate the virtual environment and run:

```bash
python -m pytest backend/tests/unit/ -v
```

Run the frontend production build as well:

```bash
cd frontend
npm run build
```

A successful unit-test run or frontend build does not by itself validate live Google OAuth, production database migrations, email delivery or the full approval/resume lifecycle.

## ⚙️ Environment configuration

Use `.env.example` as the source of truth for supported variable names. Typical configuration includes:

| Variable | Purpose |
|---|---|
| `APP_ENV` | Application environment |
| `DATABASE_URL` | SQLAlchemy database connection |
| `JWT_SECRET` | Secret used to sign application JWTs |
| `LLM_PROVIDER` | Selected model provider |
| `GROQ_API_KEY` or `OPENROUTER_API_KEY` | Provider API key, if used by the configured router |
| `OLLAMA_BASE_URL` | Local Ollama endpoint, when enabled |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret, when required by the backend flow |
| `CORS_ORIGINS` | Explicit allowed frontend origins |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` | SMTP fallback configuration, if enabled |

Not every variable is required for every provider. Review `backend/config/settings.py`, `backend/llm/router.py` and `.env.example` before configuring a new environment.

**Secret-handling rules**

- Generate a unique, high-entropy JWT secret for each environment.
- Never commit `.env`, API keys, OAuth secrets, database passwords or user tokens.
- Restrict production credentials to the minimum necessary scopes and permissions.
- Store and rotate secrets through the deployment platform's secret manager.
- Treat Google refresh tokens as sensitive credentials; HTTPS alone does not encrypt tokens at rest.

## ☁️ Deployment

The repository includes a Vercel configuration and a GitHub Actions workflow. Before deploying:

1. Verify the configured Vercel root directory and build settings.
2. Configure the required environment variables in the deployment platform.
3. Configure Google OAuth authorized origins and redirect URIs for the actual deployed domain.
4. Confirm the production database is reachable and connection limits are appropriate for serverless execution.
5. Apply schema migrations as a controlled deployment step.
6. Run smoke tests for authentication, conversation creation, approval/rejection, document generation and integrations.
7. Verify that secrets and user data are never emitted in logs or public responses.

A serverless filesystem is not durable storage. Files needed after a request should be stored in a persistent database or object store, or regenerated safely. Do not assume files under `/tmp` survive across invocations.

## 🛡️ Security model

The application combines authentication, API validation, registered tools and human approval. These are useful building blocks, but security depends on enforcement at each boundary.

Production requirements:

- **Fail-closed approval:** if the approval check fails or its state cannot be verified, block the side effect.
- **Per-user isolation:** resolve Google credentials from the authenticated user or a trusted, ownership-checked execution context only. Never fall back to another active account.
- **Authorization on every resource:** apply ownership checks to clients, quotes, invoices, documents, assignments, executions and approval decisions.
- **Least privilege:** request only the Google scopes needed for the enabled features.
- **Credential protection:** encrypt stored refresh tokens, redact logs, support revocation and avoid returning tokens to the frontend.
- **Plan validation:** allow only registered tools, validate schemas, cap plan size and reject invalid dependencies.
- **Safe retries:** use idempotency keys for actions that create records, send messages or schedule meetings.
- **Accurate status reporting:** distinguish pending, successful, failed, simulated and ambiguous external outcomes.
- **Financial integrity:** use decimal-safe money calculations and a single authoritative pricing service for database and document output.
- **Shared rate limiting:** use shared storage for rate limits when deploying multiple instances.
- **Controlled migrations:** do not rely on concurrent application startup to mutate the production schema.

These are requirements and hardening priorities, not a claim that every item is already implemented.

## 🧪 Testing

The repository includes unit tests covering areas such as request validation, execution, tool safety, email behavior, LLM routing, schema checks and security-related behavior.

Recommended release checks:

- Run the backend unit tests against a clean test database.
- Build the configured frontend using its lockfile.
- Test two different users and confirm neither can read or mutate the other's data.
- Test approval, rejection, approval-state errors and expired approvals.
- Test provider-unavailable and ambiguous email-delivery outcomes.
- Test interrupted workflows and retries for duplicate side effects.
- Test quote totals across the database, PDF, Excel and spreadsheet outputs.
- Test OAuth and external API calls in a dedicated non-production environment.

Do not interpret the presence of a test file as proof that the corresponding scenario is comprehensively covered.

## ⚠️ Known limitations and hardening priorities

The following items were identified during a static repository review and should be verified and addressed before relying on the application for sensitive production workflows:

1. **Approval failure handling:** the execution engine contains an exception path that logs an approval-check failure and continues. This should fail closed.
2. **Google account resolution:** the Google authentication helper contains a database fallback to an active user when the execution context cannot be resolved. Remove cross-user fallback and require a trusted user context.
3. **Email simulation:** the email handler can return a success-shaped result when delivery is simulated because credentials are missing. Use a distinct `not_sent` status and do not update the quote as sent.
4. **Resource ownership:** audit every read and write path—including document linking, invoice creation, approval and external integrations—for consistent owner checks.
5. **Money precision:** some commercial paths persist monetary values as floating point. Use `Decimal` in calculations and a suitable fixed-precision database type.
6. **Database lifecycle:** move production schema changes into migrations and avoid startup-time schema mutation.
7. **Rate limiting:** in-memory counters are not shared across serverless instances. Use shared storage where multi-instance protection is required.
8. **Workflow reliability:** validate plans before execution and add idempotency and durable action outcomes before enabling broad automatic retries.
9. **Deployment verification:** the repository contains multiple frontend directories and should have one clearly documented deployment source of truth.

This list is based on source inspection. It is not a dynamic security audit, penetration test or verification of the live deployment. Re-run tests and review the relevant code after changes to confirm that each issue is resolved.

## 🗺️ Roadmap

- [ ] Make all approval checks fail closed and test rejection/error paths.
- [ ] Enforce ownership-aware Google credential resolution.
- [ ] Separate simulated email attempts from provider-confirmed delivery.
- [ ] Standardize tenant/resource authorization across API and tool handlers.
- [ ] Centralize pricing calculations and use fixed-precision money storage.
- [ ] Validate all AI-generated plans and tool arguments.
- [ ] Add idempotency for external and financial side effects.
- [ ] Apply database migrations as a controlled release step.
- [ ] Add end-to-end tests for multi-user isolation and approval/resume behavior.
- [ ] Document one canonical frontend and repeatable deployment procedure.

## 📄 Privacy and terms

- [Privacy policy](https://agent.yahya.ink/privacy)
- [Terms of service](https://agent.yahya.ink/terms)

---

**Built by Yahya Bouchak.**

For issues and technical discussion, use the [GitHub repository](https://github.com/Bouchask/Commercial_AI_Agent).
