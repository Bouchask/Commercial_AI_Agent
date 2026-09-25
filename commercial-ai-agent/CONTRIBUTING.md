# 🤝 Guide de Contribution

Merci de votre intérêt pour contribuer à **Commercial AI Agent** ! Ce guide vous aidera à démarrer.

## 📋 Prérequis

- Python 3.11+
- Node.js 20+
- PostgreSQL (ou SQLite pour le développement local)
- Git

## 🚀 Mise en Place de l'Environnement

```bash
# Cloner le dépôt
git clone https://github.com/Bouchask/assitance-ai.git
cd assitance-ai/commercial-ai-agent

# Backend
python -m venv backend/venv
source backend/venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Frontend
cd frontend && npm install && cd ..
```

## 🧪 Lancer les Tests

```bash
# Tests unitaires
python -m pytest backend/tests/unit/ -v

# Tests d'intégration
python -m pytest backend/tests/integration/ -v

# Tous les tests
python -m pytest backend/tests/ -v
```

## 📝 Conventions de Code

### Python (Backend)
- **Style** : PEP 8 (max 160 caractères par ligne)
- **Imports** : Toujours en tête de fichier, jamais à l'intérieur des fonctions
- **Exceptions** : Toujours spécifier le type (`except ValueError:`, jamais `except:`)
- **Type hints** : Obligatoires pour toutes les fonctions publiques
- **Docstrings** : Format Google style pour les classes et fonctions publiques
- **Logging** : Utiliser `logger = logging.getLogger(__name__)`, jamais `print()`

### JavaScript (Frontend)
- **Framework** : React 19 + Vite
- **Styling** : TailwindCSS v4
- **Composants** : Fonctionnels avec hooks

## 🔀 Workflow Git

1. Créez une branche depuis `main` : `git checkout -b feature/ma-fonctionnalite`
2. Committez avec des messages conventionnels :
   - `feat:` pour une nouvelle fonctionnalité
   - `fix:` pour une correction de bug
   - `docs:` pour la documentation
   - `test:` pour les tests
   - `refactor:` pour du refactoring
3. Poussez et créez une Pull Request vers `main`

## 🏗️ Structure du Projet

```
backend/
├── agents/       # Agents IA (PromptEngineer, Planner, Executor, Response)
├── api/          # Routes Flask REST
├── mcp/          # Outils MCP (database, email, calendar, sheets, document)
├── models/       # Modèles SQLAlchemy
├── execution/    # Moteur d'exécution et machine à états
├── llm/          # Routeur LLM multi-provider
├── services/     # Services métier (LaTeX, Excel, pricing)
└── tests/        # Tests unitaires et d'intégration

frontend/src/
├── pages/        # Pages React (Dashboard, Login)
├── components/   # Composants UI réutilisables
└── index.css     # Système de design
```

## 📞 Contact

Pour toute question : **bouchakyahya0@gmail.com**
