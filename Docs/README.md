# SupportDesk AI: AI-Powered Customer Support Ticketing System

A Flask + PostgreSQL ticketing system that sorts customer queries with machine learning, flags angry customers, suggests replies from a knowledge base using RAG (LangChain + FAISS), tracks SLAs and agent performance, and pushes real-time alerts with Flask-SocketIO.

## The problem

Companies receive thousands of customer queries. Sorting them, routing them to the right agent and answering quickly is slow and expensive, and angry customers wait too long. SupportDesk AI automates the sorting and speeds up the replies.

## Features

- **Ticket workflow:** create, assign, reply and close tickets, with a full conversation thread.
- **Automatic classification:** a scikit-learn model sets the category (Billing, Technical, Refund), priority and sentiment as the agent types, with a live AI preview.
- **Angry customer detection:** sentiment analysis flags angry customers, and the ticket is automatically marked Urgent.
- **RAG reply suggestions:** the ticket text is matched against the knowledge base with FAISS semantic search. An optional "Generate with AI" button asks Gemini to write a reply using only the retrieved articles.
- **SLA tracking:** every ticket gets a deadline from its priority (Urgent 1 h, High 4 h, Normal 12 h, Low 24 h). A Celery job checks every minute and notifies the agent and admins once when a ticket is breached.
- **Agent performance dashboard:** open and resolved tickets, average first reply time and SLA met % per agent.
- **Real-time notifications:** Flask-SocketIO toasts and a live unread badge, also for events raised by background workers.

## How the AI works

| Part | Implementation |
|---|---|
| Category, priority, sentiment | TF-IDF + Logistic Regression (scikit-learn), one model per target |
| Business rule | An `Angry` sentiment always forces `Urgent` priority |
| Retrieval | `all-MiniLM-L6-v2` embeddings (sentence-transformers) stored in a FAISS index through LangChain |
| Reply generation | Gemini (optional), prompted to use only the retrieved articles |
| Background jobs | Celery worker + beat on Redis |
| Real time | Flask-SocketIO with a Redis message queue |

## Tech stack

Flask, SQLAlchemy, Flask-Migrate, PostgreSQL, Flask-Login, scikit-learn, pandas, LangChain, FAISS, sentence-transformers, Google Gemini (optional), Celery, Redis, Flask-SocketIO, Jinja2, HTML/CSS/JavaScript.

## Project structure

```
Backend/
├── app/
│   ├── models/          # SQLAlchemy models (users, customers, tickets, messages, kb_articles, notifications, sla_policies)
│   ├── routes/          # auth.py and main.py (pages and AI endpoints)
│   ├── services/        # classifier.py, rag.py, notify.py
│   ├── tasks/           # Celery tasks (SLA breach check)
│   ├── templates/       # Jinja2 pages
│   ├── static/          # css and js
│   ├── celery_app.py, extensions.py, sockets.py, __init__.py
├── ml_models/           # training_data.csv (trained .pkl files are generated)
├── knowledge_base/      # FAISS index (generated)
├── migrations/          # Alembic migrations
├── build_index.py       # builds the FAISS index
├── train_models.py      # trains the 3 ML models
├── seed.py              # demo agents, customers, tickets, KB articles
├── celery_worker.py, run.py, config.py
├── requirements.txt
└── .env.example
```

## Getting started

**Requirements:** Python 3.11+, PostgreSQL, Redis (on Windows use [Memurai](https://www.memurai.com) Developer Edition), Git.

```bash
# 1. Clone and enter the project
git clone https://github.com/faizanjutt473/AI-Customer-Support-Ticketing-System.git
cd AI-Customer-Support-Ticketing-System

# 2. Virtual environment and dependencies
python -m venv venv
venv\Scripts\activate          # Windows   (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt

# 3. Configuration: copy .env.example to .env and fill it in
#    (create an empty PostgreSQL database named supportdesk first)

# 4. Create the tables and load the demo data
flask --app run db upgrade
python seed.py

# 5. Train the ML models and build the knowledge-base index
python train_models.py
python build_index.py
```

Run the three processes in separate terminals (Redis must be running):

```bash
python run.py                                                  # web app on http://127.0.0.1:5000
celery -A celery_worker.celery_app worker --pool=solo -l info  # background worker (--pool=solo is for Windows)
celery -A celery_worker.celery_app beat -l info                # runs the SLA check every minute
```

### Demo logins

| Email | Password | Role |
|---|---|---|
| ayesha@supportdesk.pk | demo1234 | admin |
| bilal@supportdesk.pk | demo1234 | agent |

These accounts are for local development only. Change them before any real deployment.

### Optional: Gemini replies

Add `GOOGLE_API_KEY` (from Google AI Studio) and `GEMINI_MODEL` to `.env`. Without a key, semantic search and the template reply still work; only the "Generate with AI" button is disabled.

## Screenshots

Add screenshots of the dashboard, ticket detail page and notifications here.

## Known limitations and roadmap

- The ML models are trained on **template-generated demo data**, so the reported accuracy is not realistic. Retrain `train_models.py` with real labelled tickets (same columns as `ml_models/training_data.csv`).
- CSRF protection (Flask-WTF `CSRFProtect`) is not enabled yet.
- Tickets are created by agents; there is no customer portal or email intake yet.
- Planned: Docker setup, automated tests, knowledge-base management page, customer satisfaction ratings.
