# ============================================================
#  AGENT_INSTRUCTIONS — Interview Trainer Agent
#  This file controls ALL agent behaviours.
#  Edit values here; changes take effect on next app restart.
# ============================================================

AGENT_INSTRUCTIONS = {

    # ----------------------------------------------------------
    # 1. INTERVIEW DIFFICULTY
    #    Controls complexity of generated questions and depth
    #    of follow-up probes.
    #    Options: "easy" | "medium" | "hard"
    # ----------------------------------------------------------
    "difficulty": "medium",

    # Difficulty-specific guidance injected into the prompt
    "difficulty_prompts": {
        "easy": (
            "Ask straightforward, entry-level questions. "
            "Prefer definitions, simple scenarios, and basic concepts. "
            "Avoid deep algorithmic or system-design topics."
        ),
        "medium": (
            "Mix conceptual, applied, and scenario-based questions. "
            "Include at least one design or trade-off question. "
            "Appropriate for 2–5 years of experience."
        ),
        "hard": (
            "Focus on advanced system design, complex trade-offs, "
            "edge cases, and leadership/ownership questions. "
            "Appropriate for senior / staff-level candidates."
        ),
    },

    # ----------------------------------------------------------
    # 2. QUESTION CATEGORIES
    #    Categories that may be included in a session.
    #    Set enabled=True/False to turn a category on or off.
    #    weight = relative probability of a question being drawn
    #    from this category (normalised internally).
    # ----------------------------------------------------------
    "question_categories": {
        "hr": {
            "enabled": True,
            "weight": 2,
            "description": "HR / Behavioural — motivation, teamwork, culture fit",
        },
        "technical": {
            "enabled": True,
            "weight": 3,
            "description": "Technical — domain knowledge, coding, system design",
        },
        "behavioral": {
            "enabled": True,
            "weight": 2,
            "description": "Behavioural STAR — past experiences and how you handled them",
        },
        "situational": {
            "enabled": True,
            "weight": 1,
            "description": "Situational — hypothetical work scenarios",
        },
        "leadership": {
            "enabled": False,
            "weight": 1,
            "description": "Leadership & ownership — managing teams and decisions",
        },
    },

    # ----------------------------------------------------------
    # 3. NUMBER OF QUESTIONS PER SESSION
    #    Recommended range: 5 – 15
    # ----------------------------------------------------------
    "num_questions": 8,

    # ----------------------------------------------------------
    # 4. FEEDBACK STYLE
    #    Controls tone and depth of answer evaluation.
    #    Options: "encouraging" | "balanced" | "strict"
    # ----------------------------------------------------------
    "feedback_style": "balanced",

    "feedback_style_prompts": {
        "encouraging": (
            "Be warm, positive, and supportive. Acknowledge strengths "
            "first, then gently suggest improvements. End with motivation."
        ),
        "balanced": (
            "Be objective and professional. Clearly highlight both "
            "strengths and areas for improvement with equal weight. "
            "Be concise and actionable."
        ),
        "strict": (
            "Be direct and rigorous. Focus primarily on gaps, "
            "inaccuracies, and missed opportunities. Do not soften "
            "criticism. Hold the candidate to a high professional bar."
        ),
    },

    # ----------------------------------------------------------
    # 5. SCORING CRITERIA
    #    Dimensions scored 0–10. Adjust weights (sum should = 1.0)
    #    for the Overall Performance calculation.
    # ----------------------------------------------------------
    "scoring_criteria": {
        "technical_knowledge": {
            "weight": 0.40,
            "description": "Accuracy, depth, and relevance of technical content",
        },
        "communication": {
            "weight": 0.25,
            "description": "Clarity, structure, and articulation of the answer",
        },
        "confidence": {
            "weight": 0.20,
            "description": "Assertiveness, certainty, and lack of filler language",
        },
        "problem_solving": {
            "weight": 0.15,
            "description": "Logical reasoning, creativity, and approach to the problem",
        },
    },

    # ----------------------------------------------------------
    # 6. LEARNING RESOURCES
    #    Appended to reports when a candidate scores below the
    #    threshold in a given topic area.
    # ----------------------------------------------------------
    "score_threshold_for_resources": 6.0,   # out of 10

    "learning_resources": {
        "default": [
            {"title": "LeetCode", "url": "https://leetcode.com"},
            {"title": "freeCodeCamp", "url": "https://www.freecodecamp.org"},
            {"title": "Coursera", "url": "https://www.coursera.org"},
        ],
        "Software Engineer": [
            {"title": "Grokking the System Design Interview", "url": "https://www.educative.io/courses/grokking-the-system-design-interview"},
            {"title": "Neetcode.io", "url": "https://neetcode.io"},
            {"title": "CS50 Harvard", "url": "https://cs50.harvard.edu"},
        ],
        "Data Analyst": [
            {"title": "Kaggle Learn", "url": "https://www.kaggle.com/learn"},
            {"title": "Mode SQL Tutorial", "url": "https://mode.com/sql-tutorial"},
            {"title": "Google Data Analytics Certificate", "url": "https://grow.google/certificates/data-analytics/"},
        ],
        "Web Developer": [
            {"title": "MDN Web Docs", "url": "https://developer.mozilla.org"},
            {"title": "The Odin Project", "url": "https://www.theodinproject.com"},
            {"title": "Frontend Masters", "url": "https://frontendmasters.com"},
        ],
        "Machine Learning Engineer": [
            {"title": "fast.ai", "url": "https://www.fast.ai"},
            {"title": "deeplearning.ai", "url": "https://www.deeplearning.ai"},
            {"title": "Papers With Code", "url": "https://paperswithcode.com"},
        ],
        "DevOps Engineer": [
            {"title": "KodeKloud", "url": "https://kodekloud.com"},
            {"title": "AWS Skill Builder", "url": "https://skillbuilder.aws"},
            {"title": "Linux Foundation Training", "url": "https://training.linuxfoundation.org"},
        ],
        "Data Scientist": [
            {"title": "Kaggle Learn", "url": "https://www.kaggle.com/learn"},
            {"title": "StatQuest YouTube", "url": "https://www.youtube.com/c/joshstarmer"},
            {"title": "Towards Data Science", "url": "https://towardsdatascience.com"},
        ],
    },

    # ----------------------------------------------------------
    # 7. IBM GRANITE MODEL SETTINGS
    #    Model IDs available in IBM watsonx.ai
    # ----------------------------------------------------------
    "model_id": "ibm/granite-3-3-8b-instruct",

    "model_params": {
        "max_new_tokens": 1200,
        "min_new_tokens": 50,
        "temperature": 0.7,
        "top_k": 50,
        "top_p": 0.9,
        "repetition_penalty": 1.1,
    },

    # ----------------------------------------------------------
    # 8. SYSTEM PROMPT IDENTITY
    #    Core identity injected at the start of every LLM call.
    # ----------------------------------------------------------
    "system_identity": (
        "You are an expert AI Interview Coach powered by IBM Granite. "
        "You have deep knowledge across software engineering, data science, "
        "web development, DevOps, and business analysis. "
        "You are professional, precise, and focused on helping candidates "
        "succeed in technical interviews. Always respond in valid JSON "
        "when instructed to do so."
    ),
}
