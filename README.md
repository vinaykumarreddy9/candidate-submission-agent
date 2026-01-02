# 💼 DIGOT AI | Recruitment Orchestrator

A sophisticated multi-agent recruitment pipeline designed to automate candidate screening and outreach. Built with **LangGraph**, **FastAPI**, and **Streamlit**, this system leverages high-performance LLMs (via Groq) to provide structured, intelligent candidate evaluations with human oversight.

---

## 🌟 Key Features

- **Automated Screening**: Cross-references candidate resumes (**PDF Support**) against detailed job descriptions using AI-driven technical matching.
- **Token-Savvy Processing**: Advanced text cleaning and whitespace normalization to optimize context window usage.
- **Supervisor Architecture**: Orchestrated via a central Intelligence Supervisor for dynamic, state-aware task routing.
- **Human-in-the-Loop (HITL)**: Mandatory manual approval via Streamlit before any outreach emails are dispatched.
- **Intelligent Outreach**: Automatically drafts personalized, grounded outreach emails for qualified technical matches (Score > 85).
- **Interactive Dashboard**: A modern Streamlit interface for seamless job intake and real-time pipeline monitoring.
- **Architecture Visualization**: Built-in tools to generate and view the system's agentic topology.

---

## 🏗️ Architecture Overview

The system is organized into three core logical layers:

1.  **/agent**: The brain of the system. Contains the LangGraph definition, Supervisor node, specialized processing nodes, and centralized state management.
2.  **/backend**: A high-performance FastAPI service that exposes the recruitment pipeline and HITL approval endpoints.
3.  **/frontend**: A sleek Streamlit application providing the primary interface for recruiters.

---

## 🛠️ Tech Stack

- **Orchestration**: [LangGraph](https://github.com/langchain-ai/langgraph)
- **API Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **UI Framework**: [Streamlit](https://streamlit.io/)
- **LLM Engine**: [Groq](https://groq.com/) (Llama-3.3-70B)
- **PDF Extraction**: PyPDF2
- **Observability**: [LangSmith](https://smith.langchain.com/)

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10 or higher
- [Groq API Key](https://console.groq.com/)
- [SMTP Credentials](https://support.google.com/mail/answer/185833?hl=en) (for email outreach)

### 2. Environment Setup
Create a `.env` file in the root directory:

```env
# AI Models
GROQ_API_KEY=your_groq_api_key_here

# SMTP Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SENDER_EMAIL=your_email@gmail.com

# Backend Config
BACKEND_URL=http://localhost:8000
```

### 3. Installation
```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Running the Application

**Terminal 1: Backend API**
```powershell
uvicorn backend.main:app --reload
```

**Terminal 2: Frontend Dashboard**
```powershell
streamlit run frontend/app.py
```

---

## 📊 Architecture Visualization

To generate a fresh diagram of the agentic flow:
```powershell
$env:PYTHONPATH="."; python architecture/generate_diagrams.py
```
A PNG will be saved to `architecture/agent_architecture.png`.

---

## 🛡️ License
Distributed under the MIT License. See `LICENSE` for more information.

---
*Powered by DIGOT AI | Engineered for precision recruitment.*
