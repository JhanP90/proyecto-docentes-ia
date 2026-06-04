import os
import google.generativeai as genai
from core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

try:
    print("Available models:")
    for m in genai.list_models():
        print(m.name, m.supported_generation_methods)
except Exception as e:
    print("Error listing models:", e)
