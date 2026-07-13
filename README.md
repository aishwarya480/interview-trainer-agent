# Interview Trainer Agent
### Powered by IBM watsonx.ai · IBM Granite

An AI-powered interview preparation web application that analyses your resume, generates role-specific interview questions using **IBM Granite**, evaluates your answers across 4 performance dimensions, and produces a downloadable PDF report.

---

## Features

| Feature | Details |
|---|---|
| Resume Analysis | Upload PDF resume; AI extracts context to personalise questions |
| Role-Based Questions | 10+ job roles supported; questions tailored per role |
| 4-Dimension Scoring | Technical Knowledge · Communication · Confidence · Problem Solving |
| Smart Feedback | Strengths, improvements, model answer, per-question feedback |
| PDF Report | Downloadable performance report with scores, charts, resources |
| Dark Mode | Full light/dark theme with system-level persistence |
| Mobile Responsive | Works on all screen sizes |
| AGENT_INSTRUCTIONS | Single config file controls all AI behaviour |

---

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.10+ |
| pip | latest |
| IBM Cloud account | Free tier works |
| IBM watsonx.ai project | Required |

---

## Quick Start

### 1. Clone / Download

```bash
git clone <your-repo>
cd interview-trainer
```

### 2. Create virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your IBM Cloud credentials:

```env
IBM_API_KEY=your_ibm_cloud_api_key_here
IBM_PROJECT_ID=your_watsonx_project_id_here
WATSONX_URL=https://us-south.ml.cloud.ibm.com
FLASK_SECRET_KEY=some-random-string-here
```

#### How to get IBM credentials

1. Go to [IBM Cloud Console](https://cloud.ibm.com)
2. Create a **watsonx.ai** service instance
3. Go to **Manage → IAM → API keys** → Create API key
4. Open your watsonx.ai project → **Manage** tab → copy the **Project ID**

### 5. Run the application

```bash
python app.py
```

Open your browser at **http://localhost:5000**

---

## Customising Agent Behaviour

All AI behaviour is controlled from [`agent_instructions.py`](agent_instructions.py). You can also override key settings via `.env`.

```python
# agent_instructions.py

AGENT_INSTRUCTIONS = {

    # Interview difficulty: "easy" | "medium" | "hard"
    "difficulty": "medium",

    # Number of questions per session
    "num_questions": 8,

    # Feedback tone: "encouraging" | "balanced" | "strict"
    "feedback_style": "balanced",

    # Enable/disable question categories
    "question_categories": {
        "hr":          { "enabled": True,  "weight": 2 },
        "technical":   { "enabled": True,  "weight": 3 },
        "behavioral":  { "enabled": True,  "weight": 2 },
        "situational": { "enabled": True,  "weight": 1 },
        "leadership":  { "enabled": False, "weight": 1 },
    },

    # Scoring weights (must sum to 1.0)
    "scoring_criteria": {
        "technical_knowledge": { "weight": 0.40 },
        "communication":       { "weight": 0.25 },
        "confidence":          { "weight": 0.20 },
        "problem_solving":     { "weight": 0.15 },
    },

    # IBM Granite model
    "model_id": "ibm/granite-3-3-8b-instruct",
}
```

### .env overrides (optional)

```env
INTERVIEW_DIFFICULTY=hard
NUM_QUESTIONS=12
FEEDBACK_STYLE=strict
QUESTION_CATEGORIES=technical,behavioral
```

---

## Project Structure

```
interview-trainer/
├── app.py                  # Flask backend + IBM watsonx.ai integration
├── agent_instructions.py   # AI agent configuration (edit this)
├── requirements.txt
├── .env.example
├── .env                    # Your credentials (DO NOT commit)
├── uploads/                # Temporary resume storage
├── reports/                # Generated PDF reports
├── templates/
│   └── index.html          # Single-page frontend
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── app.js
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Main app page |
| POST | `/api/generate-questions` | Upload resume + generate questions |
| POST | `/api/evaluate-answer` | Evaluate a single answer |
| POST | `/api/generate-report` | Generate downloadable PDF report |
| GET | `/api/health` | Health check |

### POST `/api/generate-questions`

**Form data:**
```
resume:   <pdf file>
job_role: "Software Engineer"
```

**Response:**
```json
{
  "session_id": "abc123",
  "job_role": "Software Engineer",
  "questions": [
    { "id": 1, "question": "...", "category": "technical", "difficulty": "medium" }
  ]
}
```

### POST `/api/evaluate-answer`

**JSON body:**
```json
{
  "question": "What is a REST API?",
  "answer": "REST stands for...",
  "job_role": "Software Engineer",
  "category": "technical"
}
```

**Response:**
```json
{
  "scores": {
    "technical_knowledge": 8,
    "communication": 7,
    "confidence": 6,
    "problem_solving": 7
  },
  "overall_score": 7.25,
  "strengths": ["..."],
  "improvements": ["..."],
  "feedback": "...",
  "ideal_answer_summary": "..."
}
```

---

## Deployment

### Option 1 — Local (development)

```bash
python app.py
```

### Option 2 — Gunicorn (production-ready)

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Option 3 — Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
```

```bash
docker build -t interview-trainer .
docker run -p 5000:5000 --env-file .env interview-trainer
```

### Option 4 — IBM Code Engine

```bash
# Install IBM Cloud CLI + Code Engine plugin
ibmcloud login
ibmcloud ce project create --name interview-trainer
ibmcloud ce application create \
  --name interview-trainer-app \
  --image us.icr.io/YOUR_NAMESPACE/interview-trainer:latest \
  --env-from-secret interview-trainer-secrets \
  --port 5000
```

### Option 5 — Heroku

```bash
echo "web: gunicorn app:app" > Procfile
heroku create your-app-name
heroku config:set IBM_API_KEY=xxx IBM_PROJECT_ID=yyy WATSONX_URL=zzz
git push heroku main
```

---

## Supported Job Roles

- Software Engineer
- Data Analyst
- Web Developer
- Machine Learning Engineer
- DevOps Engineer
- Data Scientist
- Product Manager
- Business Analyst
- Cloud Architect
- Cybersecurity Analyst

---

## Security Notes

- **Never commit** your `.env` file — it is listed in `.gitignore`
- API keys are loaded via `python-dotenv` — not hardcoded
- Uploaded resumes are stored in `/uploads` — clean periodically in production
- Add authentication middleware before deploying publicly

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `IBM_API_KEY not set` | Ensure `.env` exists and has correct key |
| `PDF extraction empty` | Try a text-based PDF (not a scanned image) |
| `JSON parse error from LLM` | Try a different difficulty level or retry |
| `Model not found` | Check `model_id` in `agent_instructions.py` matches available Granite models |
| Port already in use | Change port: `app.run(port=5001)` |

---

## License

MIT License — free to use, modify, and distribute.

---

*Built with IBM watsonx.ai · IBM Granite · Flask · Bootstrap 5*
