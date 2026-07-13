"""
Interview Trainer Agent — Flask Backend
Powered by IBM watsonx.ai (IBM Granite)
"""

import os
import json
import re
import uuid
import logging
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

import pdfplumber
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER

from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

from agent_instructions import AGENT_INSTRUCTIONS

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))

UPLOAD_FOLDER = Path(os.getenv("UPLOAD_FOLDER", "uploads"))
REPORTS_FOLDER = Path(os.getenv("REPORTS_FOLDER", "reports"))
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
REPORTS_FOLDER.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {"pdf"}

# ---------------------------------------------------------------------------
# IBM watsonx.ai client
# ---------------------------------------------------------------------------
_wx_model: ModelInference | None = None


def get_model() -> ModelInference:
    global _wx_model
    if _wx_model is None:
        api_key = os.getenv("IBM_API_KEY")
        project_id = os.getenv("IBM_PROJECT_ID")
        wx_url = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        if not api_key or not project_id:
            raise ValueError(
                "IBM_API_KEY and IBM_PROJECT_ID must be set in your .env file."
            )
        credentials = Credentials(api_key=api_key, url=wx_url)
        ai = AGENT_INSTRUCTIONS
        _wx_model = ModelInference(
            model_id=ai["model_id"],
            credentials=credentials,
            project_id=project_id,
            params=ai["model_params"],
        )
        log.info("watsonx.ai model initialised: %s", ai["model_id"])
    return _wx_model


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_pdf_text(path: Path) -> str:
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n".join(text_parts).strip()


def build_prompt(system: str, user: str) -> str:
    return f"<|system|>\n{system}\n<|user|>\n{user}\n<|assistant|>\n"


def call_llm(user_prompt: str, system_prompt: str | None = None) -> str:
    ai = AGENT_INSTRUCTIONS
    system = system_prompt or ai["system_identity"]
    prompt = build_prompt(system, user_prompt)
    model = get_model()
    response = model.generate_text(prompt=prompt)
    return response.strip()


def extract_json(raw: str) -> dict | list:
    """Strip markdown fences and parse JSON."""
    raw = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
    # Find first JSON object or array
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", raw)
    if match:
        return json.loads(match.group(1))
    return json.loads(raw)


def resolve_difficulty() -> str:
    env_val = os.getenv("INTERVIEW_DIFFICULTY")
    return env_val if env_val in ("easy", "medium", "hard") else AGENT_INSTRUCTIONS["difficulty"]


def resolve_feedback_style() -> str:
    env_val = os.getenv("FEEDBACK_STYLE")
    return env_val if env_val in ("encouraging", "balanced", "strict") else AGENT_INSTRUCTIONS["feedback_style"]


def resolve_num_questions() -> int:
    try:
        return int(os.getenv("NUM_QUESTIONS", AGENT_INSTRUCTIONS["num_questions"]))
    except (ValueError, TypeError):
        return AGENT_INSTRUCTIONS["num_questions"]


def enabled_categories() -> list[str]:
    cats = AGENT_INSTRUCTIONS["question_categories"]
    env_cats = os.getenv("QUESTION_CATEGORIES", "")
    if env_cats:
        requested = [c.strip() for c in env_cats.split(",")]
        return [c for c in requested if c in cats and cats[c]["enabled"]]
    return [k for k, v in cats.items() if v["enabled"]]


def overall_score(scores: dict) -> float:
    criteria = AGENT_INSTRUCTIONS["scoring_criteria"]
    total = 0.0
    for key, meta in criteria.items():
        val = scores.get(key, 0)
        total += float(val) * meta["weight"]
    return round(total, 2)


def get_resources(job_role: str, score: float) -> list[dict]:
    threshold = AGENT_INSTRUCTIONS["score_threshold_for_resources"]
    if score >= threshold:
        return []
    resources = AGENT_INSTRUCTIONS["learning_resources"]
    role_resources = resources.get(job_role, [])
    default = resources.get("default", [])
    combined = role_resources + [r for r in default if r not in role_resources]
    return combined[:6]


# ---------------------------------------------------------------------------
# Route: Home
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    job_roles = [
        "Software Engineer",
        "Data Analyst",
        "Web Developer",
        "Machine Learning Engineer",
        "DevOps Engineer",
        "Data Scientist",
        "Product Manager",
        "Business Analyst",
        "Cloud Architect",
        "Cybersecurity Analyst",
    ]
    return render_template("index.html", job_roles=job_roles)


# ---------------------------------------------------------------------------
# Route: Upload Resume & Generate Questions
# ---------------------------------------------------------------------------

@app.route("/api/generate-questions", methods=["POST"])
def generate_questions():
    if "resume" not in request.files:
        return jsonify({"error": "No resume file uploaded."}), 400
    file = request.files["resume"]
    job_role = request.form.get("job_role", "Software Engineer").strip()

    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF resumes are accepted."}), 400

    filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
    filepath = UPLOAD_FOLDER / filename
    file.save(filepath)

    try:
        resume_text = extract_pdf_text(filepath)
    except Exception as exc:
        log.exception("PDF extraction failed")
        return jsonify({"error": f"Could not read PDF: {exc}"}), 500

    if not resume_text:
        return jsonify({"error": "Resume appears empty or unreadable."}), 400

    difficulty = resolve_difficulty()
    num_q = resolve_num_questions()
    cats = enabled_categories()
    diff_hint = AGENT_INSTRUCTIONS["difficulty_prompts"][difficulty]
    cats_desc = ", ".join(cats)

    user_prompt = f"""
You are generating interview questions for a {job_role} candidate.

RESUME SUMMARY:
{resume_text[:3000]}

INSTRUCTIONS:
- Generate exactly {num_q} interview questions.
- Include questions from these categories: {cats_desc}.
- Difficulty level: {difficulty}. {diff_hint}
- Tailor questions to the candidate's resume where possible.
- Return ONLY a valid JSON array — no markdown, no extra text.

JSON FORMAT:
[
  {{
    "id": 1,
    "question": "...",
    "category": "technical|hr|behavioral|situational",
    "difficulty": "{difficulty}",
    "hint": "brief internal hint for the evaluator (1 sentence)"
  }},
  ...
]
"""
    try:
        raw = call_llm(user_prompt)
        questions = extract_json(raw)
        if not isinstance(questions, list):
            raise ValueError("Expected a JSON array")
    except Exception as exc:
        log.exception("Question generation failed")
        return jsonify({"error": f"AI generation failed: {exc}", "raw": raw[:500]}), 500

    session_id = uuid.uuid4().hex
    return jsonify({
        "session_id": session_id,
        "job_role": job_role,
        "difficulty": difficulty,
        "num_questions": len(questions),
        "questions": questions,
        "resume_filename": filename,
    })


# ---------------------------------------------------------------------------
# Route: Evaluate a single answer
# ---------------------------------------------------------------------------

@app.route("/api/evaluate-answer", methods=["POST"])
def evaluate_answer():
    data = request.get_json(force=True)
    question = data.get("question", "").strip()
    answer = data.get("answer", "").strip()
    job_role = data.get("job_role", "Software Engineer").strip()
    category = data.get("category", "technical").strip()

    if not question or not answer:
        return jsonify({"error": "Question and answer are required."}), 400

    feedback_style = resolve_feedback_style()
    style_hint = AGENT_INSTRUCTIONS["feedback_style_prompts"][feedback_style]
    criteria = AGENT_INSTRUCTIONS["scoring_criteria"]
    criteria_list = "\n".join(
        f'- "{k}": {v["description"]} (weight {v["weight"]})'
        for k, v in criteria.items()
    )

    user_prompt = f"""
You are evaluating a {job_role} interview answer.

QUESTION (category: {category}):
{question}

CANDIDATE'S ANSWER:
{answer}

FEEDBACK STYLE: {feedback_style}. {style_hint}

SCORING CRITERIA (each scored 0-10):
{criteria_list}

Return ONLY valid JSON with this exact structure:
{{
  "scores": {{
    "technical_knowledge": <0-10>,
    "communication": <0-10>,
    "confidence": <0-10>,
    "problem_solving": <0-10>
  }},
  "strengths": ["strength 1", "strength 2"],
  "improvements": ["improvement 1", "improvement 2"],
  "ideal_answer_summary": "2-3 sentence model answer summary",
  "feedback": "2-4 sentence personalised feedback paragraph"
}}
"""
    try:
        raw = call_llm(user_prompt)
        result = extract_json(raw)
    except Exception as exc:
        log.exception("Evaluation failed")
        return jsonify({"error": f"Evaluation failed: {exc}"}), 500

    scores = result.get("scores", {})
    result["overall_score"] = overall_score(scores)
    result["resources"] = get_resources(job_role, result["overall_score"])
    return jsonify(result)


# ---------------------------------------------------------------------------
# Route: Generate full PDF report
# ---------------------------------------------------------------------------

@app.route("/api/generate-report", methods=["POST"])
def generate_report():
    data = request.get_json(force=True)
    session_id = data.get("session_id", uuid.uuid4().hex)
    job_role = data.get("job_role", "Software Engineer")
    difficulty = data.get("difficulty", resolve_difficulty())
    qa_pairs = data.get("qa_pairs", [])           # list of {question, answer, evaluation}
    candidate_name = data.get("candidate_name", "Candidate").strip()

    if not qa_pairs:
        return jsonify({"error": "No Q&A data provided."}), 400

    filename = f"interview_report_{session_id}.pdf"
    filepath = REPORTS_FOLDER / filename

    try:
        _build_pdf_report(
            str(filepath), candidate_name, job_role, difficulty, qa_pairs
        )
    except Exception as exc:
        log.exception("PDF generation failed")
        return jsonify({"error": f"Report generation failed: {exc}"}), 500

    return send_file(
        str(filepath),
        as_attachment=True,
        download_name=f"Interview_Report_{job_role.replace(' ', '_')}.pdf",
        mimetype="application/pdf",
    )


# ---------------------------------------------------------------------------
# PDF builder
# ---------------------------------------------------------------------------

def _build_pdf_report(
    filepath: str,
    candidate_name: str,
    job_role: str,
    difficulty: str,
    qa_pairs: list,
):
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    brand_blue = colors.HexColor("#3b82d4")
    dark_bg = colors.HexColor("#1e293b")
    muted = colors.HexColor("#57606a")

    title_style = ParagraphStyle(
        "Title", parent=styles["Title"],
        fontSize=22, textColor=brand_blue, spaceAfter=4
    )
    sub_style = ParagraphStyle(
        "Sub", parent=styles["Normal"],
        fontSize=11, textColor=muted, spaceAfter=2
    )
    h2_style = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontSize=14, textColor=dark_bg, spaceBefore=12, spaceAfter=4
    )
    h3_style = ParagraphStyle(
        "H3", parent=styles["Heading3"],
        fontSize=11, textColor=brand_blue, spaceBefore=8, spaceAfter=2
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, leading=14, spaceAfter=4
    )
    label_style = ParagraphStyle(
        "Label", parent=styles["Normal"],
        fontSize=9, textColor=muted, spaceBefore=4
    )
    italic_style = ParagraphStyle(
        "Italic", parent=styles["Normal"],
        fontSize=10, leading=14, textColor=muted, spaceAfter=4
    )

    story = []

    # --- Header ---
    story.append(Paragraph("Interview Performance Report", title_style))
    story.append(Paragraph(f"Candidate: {candidate_name}", sub_style))
    story.append(Paragraph(f"Role: {job_role}  |  Difficulty: {difficulty.title()}", sub_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", sub_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=brand_blue, spaceAfter=12))

    # --- Aggregate scores ---
    all_scores = {"technical_knowledge": [], "communication": [], "confidence": [], "problem_solving": []}
    for pair in qa_pairs:
        ev = pair.get("evaluation", {})
        sc = ev.get("scores", {})
        for k in all_scores:
            if k in sc:
                all_scores[k].append(float(sc[k]))

    avg = {k: round(sum(v) / len(v), 1) if v else 0 for k, v in all_scores.items()}
    overall = overall_score(avg)

    story.append(Paragraph("Overall Performance Summary", h2_style))

    table_data = [
        ["Dimension", "Avg Score", "Out of"],
        ["Technical Knowledge", str(avg["technical_knowledge"]), "10"],
        ["Communication",        str(avg["communication"]),        "10"],
        ["Confidence",           str(avg["confidence"]),           "10"],
        ["Problem Solving",      str(avg["problem_solving"]),      "10"],
        ["OVERALL PERFORMANCE",  str(overall),                     "10"],
    ]
    col_w = [9 * cm, 4 * cm, 3 * cm]
    tbl = Table(table_data, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), brand_blue),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 10),
        ("ROWBACKGROUNDS",(0, 1), (-1, -2), [colors.HexColor("#f7f8fa"), colors.white]),
        ("BACKGROUND",    (0, -1), (-1, -1), colors.HexColor("#1e293b")),
        ("TEXTCOLOR",     (0, -1), (-1, -1), colors.white),
        ("FONTNAME",      (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ROWHEIGHT",     (0, 0), (-1, -1), 20),
        ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.5 * cm))

    # --- Score bar visual ---
    dimensions = [
        ("Technical", avg["technical_knowledge"]),
        ("Communication", avg["communication"]),
        ("Confidence", avg["confidence"]),
        ("Problem Solving", avg["problem_solving"]),
    ]
    bar_rows = []
    for dim, score in dimensions:
        filled = int(round(score))
        empty = 10 - filled
        bar = "█" * filled + "░" * empty
        bar_rows.append([dim, bar, f"{score}/10"])
    bar_tbl = Table(bar_rows, colWidths=[5 * cm, 7 * cm, 4 * cm])
    bar_tbl.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (1, 0), (1, -1), brand_blue),
        ("ALIGN",     (2, 0), (2, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(bar_tbl)
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e5e7eb"), spaceAfter=8))

    # --- Per-question detail ---
    story.append(Paragraph("Question-by-Question Breakdown", h2_style))

    for idx, pair in enumerate(qa_pairs, 1):
        q_text = pair.get("question", "N/A")
        a_text = pair.get("answer", "N/A")
        ev = pair.get("evaluation", {})
        sc = ev.get("scores", {})
        q_overall = ev.get("overall_score", "N/A")
        feedback = ev.get("feedback", "")
        strengths = ev.get("strengths", [])
        improvements = ev.get("improvements", [])
        ideal = ev.get("ideal_answer_summary", "")

        story.append(Paragraph(f"Q{idx}: {q_text}", h3_style))
        story.append(Paragraph(f"<b>Your Answer:</b>", label_style))
        story.append(Paragraph(a_text or "No answer provided.", italic_style))

        if sc:
            sc_row = [[k.replace("_", " ").title(), f"{v}/10"] for k, v in sc.items()]
            sc_row.append(["Overall", f"{q_overall}/10"])
            sc_tbl = Table(sc_row, colWidths=[9 * cm, 7 * cm])
            sc_tbl.setStyle(TableStyle([
                ("FONTSIZE",      (0, 0), (-1, -1), 9),
                ("TEXTCOLOR",     (1, 0), (-1, -1), brand_blue),
                ("FONTNAME",      (1, 0), (-1, -1), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(sc_tbl)

        if feedback:
            story.append(Paragraph(f"<b>Feedback:</b> {feedback}", body_style))
        if strengths:
            story.append(Paragraph(f"<b>Strengths:</b> {' | '.join(strengths)}", body_style))
        if improvements:
            story.append(Paragraph(f"<b>Improve:</b> {' | '.join(improvements)}", body_style))
        if ideal:
            story.append(Paragraph(f"<b>Model Answer:</b> {ideal}", italic_style))

        story.append(HRFlowable(width="100%", thickness=0.3, color=colors.HexColor("#e5e7eb"), spaceAfter=6))

    # --- Resources ---
    all_resources = get_resources(job_role, overall)
    if all_resources:
        story.append(Paragraph("Recommended Learning Resources", h2_style))
        for res in all_resources:
            story.append(Paragraph(f"• <b>{res['title']}</b> — {res['url']}", body_style))

    # --- Footer ---
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=brand_blue))
    story.append(Paragraph(
        "Generated by Interview Trainer Agent · Powered by IBM watsonx.ai (Granite)",
        ParagraphStyle("Footer", parent=styles["Normal"],
                       fontSize=8, textColor=muted, alignment=TA_CENTER)
    ))

    doc.build(story)


# ---------------------------------------------------------------------------
# Route: Health check
# ---------------------------------------------------------------------------

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "model": AGENT_INSTRUCTIONS["model_id"]})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=debug)
