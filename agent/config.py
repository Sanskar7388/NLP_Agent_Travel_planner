import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("apikey")
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/"

# Validation
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file")
