
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load env from backend/.env
load_dotenv("backend/.env")

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ No API Key found! Check backend/.env")
else:
    genai.configure(api_key=api_key)
    print("🔍 Fetching available models for your API key...")
    try:
        models = genai.list_models()
        print("\n✅ YOUR AVAILABLE MODELS:")
        for m in models:
            if 'generateContent' in m.supported_generation_methods:
                print(f" - {m.name} (Supported)")
    except Exception as e:
        print(f"❌ Error fetching models: {e}")
