import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", ".env")
loaded = load_dotenv(dotenv_path)

print(f"Loading .env from: {dotenv_path}")
print(f"Did .env load? {loaded}")

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("\n[CRITICAL ERROR] GEMINI_API_KEY NOT FOUND in environment variables.")
    print("Please check your 'backend/.env' file.")
else:
    print(f"\n[OK] Found API Key: {api_key[:5]}...{api_key[-5:]}")
    
    print("\n--- Listing Available Models ---")
    try:
        genai.configure(api_key=api_key)
        models = list(genai.list_models())
        found_any = False
        for m in models:
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
                found_any = True
        
        if not found_any:
            print("[WARNING] No models found that support 'generateContent'.")
            
    except Exception as e:
        print(f"[CRITICAL ERROR] Failed to list models: {e}")

    print("\n--- Testing Generation (Detailed Error) ---")
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content("Hello")
        print(f"[SUCCESS] Generation worked! Response: {response.text}")
    except Exception as e:
        print(f"[ERROR] Generation failed: {e}")
