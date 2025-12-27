# Real-Time Sentiment Analysis Platform

A production-grade, real-time sentiment analysis platform that processes social media posts, analyzes sentiment and emotions using AI models, and provides live visualization through a web dashboard.

![Platform Status](https://img.shields.io/badge/status-production--ready-success)
![Python](https://img.shields.io/badge/python-3.12-blue)
![React](https://img.shields.io/badge/react-18.2-blue)
![Docker](https://img.shields.io/badge/docker-compose-blue)
![License](https://img.shields.io/badge/license-MIT-blue)

## 🌟 Features

- **Real-time Processing**: Analyze social media posts in real-time using Redis Streams
- **Dual AI Analysis**: Combine local Hugging Face models with external LLM APIs (Groq/OpenAI/Anthropic)
- **Live Dashboard**: React-based dashboard with WebSocket updates and interactive charts
- **Sentiment & Emotion Detection**: Classify sentiment (positive/negative/neutral) and detect 6 emotions
- **Intelligent Alerting**: Automated alerts when negative sentiment exceeds thresholds
- **Microservices Architecture**: 6 containerized services with Docker Compose orchestration
- **Production-Ready**: Comprehensive error handling, logging, and graceful degradation

## 📋 Prerequisites

- **Docker** 20.10+ and **Docker Compose** 2.0+
- **API Key** for external LLM (Groq, OpenAI, or Anthropic) - [Get Groq API Key](https://console.groq.com/keys)
- **System Resources**: 4GB RAM minimum, 8GB recommended
- **Ports Available**: 3000 (frontend), 8000 (backend)

## 🚀 Quick Start

### 1. Clone and Configure

```bash
git clone <repository-url>
cd sentiment-analysis-platform

# Create environment file from template
cp .env.example .env

# Edit .env and add your API key
# Required: LLM_API_KEY=your_api_key_here
# Optional: Adjust other settings as needed
```

### 2. Start All Services

```bash
# Start all 6 services
docker-compose up -d

# Verify all services are running
docker-compose ps

# View logs
docker-compose logs -f
```

### 3. Access the Dashboard

Open your browser to **http://localhost:3000**

The dashboard will display:
- Real-time sentiment distribution (pie chart)
- Sentiment trends over time (line chart)
- Live post feed with sentiment badges
- Key metrics (total posts, positive/negative/neutral counts)

### 4. Send Test Data
You can simulate social media posts by sending test data to the ingestion service:

```bash
curl -X POST http://localhost:8000/ingest -H "Content-Type: application/json" -d '{"post":"I love this product!"}'
```

## 🛠️ Development

### 1. Install Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```
### 2. Run Services Locally

```bash
# Start Redis
docker run -d -p 6379:6379 redis

# Start Backend
cd ../backend
uvicorn main:app --reload

# Start Frontend
cd ../frontend
npm start
```

---

## 🏗️ Architecture Overview

A compact overview of the system and where each component lives. For the full, production-ready architecture and design decisions, see `ARCHITECTURE.md`.

```
Frontend (React, Port 3000) ↔ Backend API (FastAPI, Port 8000)
          ↑                            ↑
          └───── WebSocket / HTTP ─────┘
                 ↓          ↓
            Redis (Streams + Cache)  ←→  PostgreSQL (Persistent storage)
                 ↓
            Worker (AI processing)
                 ↓
            Ingester (data generation)
```

### Key components

- **Frontend** — React + Vite: live dashboard, WebSocket client, charts (Recharts).
- **Backend** — FastAPI: REST endpoints, WebSocket server, health checks, aggregation services.
- **Redis** — Streams: ingestion queue and L1 cache for aggregates.
- **Database** — PostgreSQL: posts, analysis results, and alerts.
- **Worker** — Async processors: local Hugging Face models + fallback LLM providers.
- **Ingester** — Synthetic or real data publishers to `sentiment_stream`.

---

## 🔬 Data Flow & Real-time Behavior

- Ingester publishes messages to Redis Streams (`sentiment_stream`) via XADD.
- Worker XREADGROUP -> analyzes messages (local model → fallback LLM) and stores results in the DB.
- Backend aggregates data, caches results in Redis, and broadcasts updates via WebSocket to the dashboard.

---

## 🤖 AI / ML Models

- Local models: `distilbert-base-uncased-finetuned-sst-2-english` (sentiment), `j-hartmann/emotion-english-distilroberta-base` (emotion).
- External providers: Groq, OpenAI, Anthropic (configurable via `LLM_PROVIDER`, `LLM_API_KEY`).
- Strategy: local first (low latency, low cost), external LLM fallback for improved accuracy.

---

## ✅ Healthchecks, Observability & Scaling

- **Backend health**: GET `/api/health` — checks DB + Redis connectivity and returns overall status.
- **Scaling**: docker-compose replica configurations or Kubernetes migration (see `ARCHITECTURE.md` for suggested auto-scaling triggers and metrics to monitor).
- **Logging & metrics**: structured logs and future Prometheus/Grafana recommendations are in `ARCHITECTURE.md`.

---

## 🧪 Testing

Run unit tests across services:

```bash
# Backend tests
cd backend
pytest -q

# Ingester tests
cd ../ingester
pytest -q

# Worker tests
cd ../worker
pytest -q
```

---

## ⚠️ Troubleshooting Tips

- If the backend shows DB connection errors, verify `DATABASE_URL` and that `db` is healthy (`pg_isready`).
- If WebSocket disconnects, check logs for `ConnectionManager` and Redis health.

---

## 📄 License & Contact

This project is open source — see the `LICENSE` file. For questions or contribution guidance, open an issue or contact the maintainers via the repository.

