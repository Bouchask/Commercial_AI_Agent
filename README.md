# Commercial AI Agent 🚀

An intelligent, LangGraph-based orchestration platform that automates the generation and management of commercial proposals (quotes/devis), invoicing, and client follow-ups through natural language. Built with a sleek Glassmorphism interface for the modern enterprise.

## ✨ Key Features

- **Conversational Intelligence**: A highly tuned `PromptEngineerAgent` capable of understanding complex user requests, maintaining short-term conversational memory, and merging context for quick amendments (e.g., "Change the discount to 30%", "Switch the client to Google").
- **Autonomous Planning**: A `PlannerAgent` that dynamically charts dependencies and selects exactly which backend tools (MCP) must be executed in what sequence to achieve the user's intent.
- **Human-in-the-Loop Validation**: Built-in approval steps for sensitive actions like sending emails or finalizing financial documents.
- **Dynamic PDF Generation**: Native integration with LaTeX templating for pixel-perfect, highly customized B2B quotes and invoices. Includes dynamic VAT/TVA calculation and proportional line item discounts.
- **Resilience & Self-Healing**: Includes fallback providers and retry exponential-backoff logic for local LLMs via `ModelRouter`.

## 🧠 Core Concepts & Architecture (MVP)

This Minimum Viable Product (MVP) demonstrates a complex multi-agent orchestration architecture utilizing the **Model Context Protocol (MCP)** for seamless integration between LLMs and backend services. The system revolves around several core concepts:

### 1. The Multi-Agent System (LangGraph)
The application doesn't rely on a single LLM call. Instead, it utilizes **LangGraph** to construct a state machine where multiple specialized agents collaborate:
- **PromptEngineerAgent**: Acts as the "brain's intake". It takes the raw user input and normalizes it into a strict JSON intent (Action, Client, Requirements). 
- **PlannerAgent**: Acts as the "logical router". It receives the structured intent from the Prompt Engineer and cross-references it with available MCP tools. It then generates an execution sequence (e.g., *Step 1: Create Client -> Step 2: Prepare Items -> Step 3: Create Quote*), managing dependencies between steps.

### 2. Short-Term Memory & Context Merging
One of the most powerful features of this MVP is its ability to handle conversational amendments gracefully. If a user rejects a quote and says *"Change the discount to 30%"*, the agent does not forget the original client or services. 
The system intercepts the rejection, passes the **Previous Context** (state history) back to the `PromptEngineerAgent`, and instructs it to merge the old state with the new request. This effectively simulates a short-term memory layer, allowing continuous modifications without relying on external heavy memory databases like Letta/MemGPT.

### 3. Model Context Protocol (MCP) Tools
All backend functions (database queries, PDF generation, email sending) are wrapped into strict schema-defined tools. These schemas are exposed to the `PlannerAgent`, guaranteeing that the LLM understands exactly what arguments are required. The current toolset includes:
- **Database Tools** (`db.find_or_create_client`, `db.create_quote`)
- **Utility Tools** (`utils.prepare_quote_items` for pricing logic)
- **Document Tools** (`document.generate` via LaTeX templating)
- **Email Tools** (`email.prepare`, `email.send`)

### 4. Human-in-the-Loop
To maintain commercial safety, certain high-risk actions (like finalizing a quote or sending an email) trigger a pause in the LangGraph execution. The frontend Dashboard intercepts this `waiting_approval` state, allowing the human operator to review the PDF and accept/reject it before the email is sent.

## 🚀 Getting Started

The deployable application lives in `commercial-ai-agent/`. Its Vite frontend
(`commercial-ai-agent/frontend`) is the canonical interface used by
`vercel.json`. The separate `frontend/dashboard-app` directory is a legacy
prototype and should not be deployed alongside it.

Before a production deploy, configure secrets in the hosting provider instead
of committing an `.env` file. Rotate any credential that may have appeared in
Git history. GitHub Actions runs the backend tests and production frontend
build on every push and pull request.

### 1. Backend Setup

```bash
cd commercial-ai-agent/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the server (runs on port 5001)
python run.py
```

### 2. Frontend Setup

```bash
cd commercial-ai-agent/frontend
npm install

# Start the dev server
npm run dev
```
Open `http://localhost:5175` in your browser.

## 🧪 Testing the Pipeline

A dedicated python test suite validates the integrity of the `PromptEngineerAgent` and `PlannerAgent` against LLM hallucinations. It checks context-merging across multiple conversation steps and asserts strict JSON structures for backend tools.

```bash
# Ensure you are at the project root with the venv active
cd commercial-ai-agent
export PYTHONPATH=.
python -m pytest backend/tests
```

## 🛠️ Modifying Templates

The PDF layouts are generated using LaTeX. To modify the core layout or add new variable tags (like custom TVA formats or company branding):
- Edit the templates located in `templates/quotes/`.
- The compilation is handled by the `LatexService` in the backend.

---
**Created by Yahya Bouchak, Master SIIA** 🎓 | Built for the Commercial AI Agent Project.
