import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print("--- Gemini Diagnostic ---")
print(f"Key exists: {'Yes' if api_key else 'No'}")
try:
    models = genai.list_models()
    print("Available Models:")
    found = False
    for m in models:
        if 'generateContent' in m.supported_generation_methods:
            print(f" - {m.name}")
            found = True
    if not found:
        print(" ! No models found with generateContent support.")
except Exception as e:
    print(f"Error: {e}")
