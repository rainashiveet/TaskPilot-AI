import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

MODEL_CONFIGS = {
    "openai": {"default_model": "gpt-4o-mini", "models": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"], "max_tokens": 2048, "temperature": 0.3},
    "gemini": {
        "default_model": "gemini-2.0-flash",
        "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-pro"],
        "max_tokens": 2048,
        "temperature": 0.3,
    },
    "groq": {"default_model": "llama-3.3-70b-versatile", "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"], "max_tokens": 2048, "temperature": 0.3},
}

TOOL_REGISTRY = {
    "summarizer":    {"name": "Summarizer",    "icon": "📝", "description": "Summarizes text into key points."},
    "task_planner":  {"name": "Task Planner",  "icon": "📅", "description": "Generates structured daily plans."},
    "calculator":    {"name": "Calculator",    "icon": "🔢", "description": "Performs arithmetic operations."},
    "text_to_tasks": {"name": "Text-to-Tasks", "icon": "✅", "description": "Converts text into actionable tasks."},
}

EXAMPLE_QUERIES = [
    {"label": "Summarize text", "text": "Summarize: The quarterly review highlighted a 15% revenue increase driven by enterprise contracts. Customer satisfaction rose to 92%. However, churn in the SMB segment increased by 3%, attributed to pricing changes. The team proposed a new tiered pricing model. Three new hires were approved for support, and cloud migration is 60% complete."},
    {"label": "Plan my day", "text": "Create a daily plan for a software developer who wants to learn AI/ML for 2 hours, exercise for 45 minutes, finish a feature PR by 5 PM, and have team standup at 10 AM."},
    {"label": "Calculate", "text": "Calculate: (1500 * 12) / 365 + 250 - 45.5"},
    {"label": "Extract tasks", "text": "Convert to tasks: We need to prepare for the client demo next Wednesday. Update the presentation slides with Q4 metrics, review the budget report for discrepancies, schedule a rehearsal with the sales team, and make sure the staging environment is running the latest build."},
    {"label": "Summarize then Tasks", "text": "Summarize this meeting notes and extract actionable tasks: The team discussed the upcoming product launch scheduled for March 15. Marketing needs the landing page ready by Feb 28. Engineering confirmed the API will be stable by March 1. QA needs 5 days for regression testing. Legal is reviewing the privacy policy update. Sarah will coordinate with the design team for new assets by Feb 20."},
    {"label": "Plan then Tasks", "text": "Create a study plan for learning Python data science in 4 weeks, then break it down into specific tasks I can track."},
]