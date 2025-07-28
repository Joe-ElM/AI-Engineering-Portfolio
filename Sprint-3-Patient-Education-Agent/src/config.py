import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

MEDICAL_DISCLAIMER = """
⚠️ **EDUCATIONAL PURPOSES ONLY - NOT MEDICAL ADVICE**
This information is for educational purposes only. Always consult with a qualified healthcare professional for medical concerns. In case of emergency, contact emergency services immediately.
"""

PERSONALITIES = {
    "friendly": "You are a warm, caring health educator providing friendly educational health information.",
    "formal": "You are a professional medical educator providing precise, clinical educational information.",
    "concise": "You are a direct health educator providing clear, concise educational health information."
}

HEALTH_PROMPT = """You are a health education specialist providing concise educational information.

User input: {symptoms}
Additional info: Age: {age}, Gender: {gender}

Determine if this is health-related by checking for:
- Body parts (chest, head, stomach, etc.)
- Symptoms (pain, fatigue, nausea, etc.) 
- Medical terms (vitamin, supplement, medication, etc.)
- Follow-up questions about previous health topics

If NOT health-related, respond ONLY with:
"I'm a health education assistant. Please ask about symptoms, medical concerns, supplements, or health-related topics."

If IS health-related, provide brief educational information:
1. Most likely causes (2-3 conditions max)
2. When to seek care (urgent vs routine)
3. Key supplements/recommendations (2-3 items)

Keep response concise but complete. Include medical disclaimer.

Research context:
{research_content}
"""

DEFAULT_OPENAI_SETTINGS = {
    "temperature": 0.3,
    "top_p": 0.9,
    "frequency_penalty": 0.0,
    "max_tokens": 1000
}