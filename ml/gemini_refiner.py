import os
import google.generativeai as genai
from PIL import Image
import json
import time
from dotenv import load_dotenv

# ── EasyOCR (lazy init) ──────────────────────────────────────────
_ocr_reader = None

def _get_ocr():
    """Lazy-load EasyOCR to avoid slow startup."""
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import easyocr
            # lang_list=['en'] covers MJCET posters well
            _ocr_reader = easyocr.Reader(['en'], gpu=False) 
            print("[OCR] EasyOCR initialized ✅")
        except Exception as e:
            print(f"[OCR] EasyOCR not available: {e}")
            _ocr_reader = False
    return _ocr_reader if _ocr_reader else None

def extract_text_from_image(image_path):
    """Run EasyOCR on poster image and return all extracted text."""
    reader = _get_ocr()
    if not reader:
        return ""
    try:
        # result is a list of (bbox, text, confidence)
        result = reader.readtext(image_path)
        lines = [res[1] for res in result if res[2] > 0.2] # Only keep confident text
        text = " | ".join(lines)
        if lines:
            print(f"[OCR] Extracted {len(lines)} segments from poster")
        return text
    except Exception as e:
        print(f"[OCR] Extraction failed: {e}")
        return ""
_whisper_model = None

def _get_whisper():
    """Lazy-load Whisper model."""
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper
            # 'tiny' or 'base' are fast for short reel clips
            _whisper_model = whisper.load_model("base")
            print("[WHISPER] Model loaded ✅")
        except Exception as e:
            print(f"[WHISPER] Model failed to load: {e}")
            _whisper_model = False
    return _whisper_model if _whisper_model else None

def transcribe_audio(audio_path):
    """Transcribe audio from a reel using Whisper."""
    model = _get_whisper()
    if not model or not os.path.exists(audio_path):
        return ""
    try:
        print(f"[WHISPER] Transcribing: {os.path.basename(audio_path)}...")
        result = model.transcribe(audio_path)
        text = result.get("text", "").strip()
        print(f"[WHISPER] Done: {text[:50]}...")
        return text
    except Exception as e:
        print(f"[WHISPER] Transcription failed: {e}")
        return ""

# Force load .env from the backend folder
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend', '.env')
load_dotenv(env_path)

# ── Load up to 5 API keys ──────────────────────────────────────────
# In backend/.env, add keys as:
#   GEMINI_API_KEY=key1
#   GEMINI_API_KEY_2=key2
#   GEMINI_API_KEY_5=key5
#   GEMINI_API_KEY_6=key6
#   GEMINI_API_KEY_7=key7
_key_env_names = ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3",
                  "GEMINI_API_KEY_4", "GEMINI_API_KEY_5", "GEMINI_API_KEY_6", "GEMINI_API_KEY_7"]
ALL_KEYS = [os.getenv(k) for k in _key_env_names if os.getenv(k)]

if not ALL_KEYS:
    print("[GEMINI] ❌ No API keys found in backend/.env!")
else:
    print(f"[GEMINI] Loaded {len(ALL_KEYS)} API key(s)")

# ── Model preference (confirmed working 2026-02-24) ────────────────
MODEL_CANDIDATES = [
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-flash-lite-latest",
]

# ── Active state ────────────────────────────────────────────────────
_current_key_idx = 0
_active_model = None
_active_model_name = None

def _make_model(key_idx, model_name):
    """Create a model object for the given key+model WITHOUT a smoke test (saves quota)."""
    global _active_model, _active_model_name, _current_key_idx
    try:
        genai.configure(api_key=ALL_KEYS[key_idx])
        _active_model = genai.GenerativeModel(model_name)
        _active_model_name = model_name
        _current_key_idx = key_idx
        print(f"[GEMINI] ✅ Using key #{key_idx + 1} → {model_name}")
        return True
    except Exception as e:
        if "404" in str(e):
            return False   # Model not available
        return False

def _init():
    """Initialize with first available key+model combo."""
    for ki in range(len(ALL_KEYS)):
        for model_name in MODEL_CANDIDATES:
            if _make_model(ki, model_name):
                return
    print("[GEMINI] ❌ Could not initialize any model.")

_init()

def _switch_to_next_key():
    """Try the next key with the same model. Returns True if successful."""
    global _current_key_idx
    next_idx = _current_key_idx + 1
    while next_idx < len(ALL_KEYS):
        if _make_model(next_idx, _active_model_name):
            return True
        next_idx += 1
    return False  # All keys exhausted

# ── Main function ───────────────────────────────────────────────────
def refine_event_with_gemini(image_path, caption, qr_hint=None, audio_transcription=None):
    """
    Analyze event poster image + caption + transcription → return structured event dict.
    Auto-switches API key on quota hit.
    """
    global _active_model

    if not ALL_KEYS or not _active_model:
        print("[GEMINI] No keys or model available.")
        return None

    # ── Resolve image path ──────────────────────────────────────────
    if not os.path.exists(image_path):
        alt = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "images", os.path.basename(image_path)
        )
        if os.path.exists(alt):
            image_path = alt
        else:
            print(f"[GEMINI] Image not found: {image_path}")
            return None

    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f"[GEMINI] Cannot open image: {e}")
        return None

    qr_context = (
        f'Special Hint: A QR code on the poster links to: {qr_hint}. Use this as the registration_link.'
        if qr_hint else ""
    )

    # ── OCR: extract all visible text from the poster image ────────
    ocr_text = extract_text_from_image(image_path)
    ocr_context = (
        f"\nPoster OCR Text (all text extracted directly from the image): {ocr_text}"
        if ocr_text else ""
    )

    audio_context = (
        f"\nAudio Transcription (what was spoken in the reel): {audio_transcription}"
        if audio_transcription else ""
    )

    prompt = f"""You are analyzing an MJCET college event poster image and its Instagram caption.
{qr_context}{ocr_context}{audio_context}

CRITICAL: We only want UPCOMING events. 
If this post is a RECAP, GLIMPSE, HIGHLIGHTS of a past event, or a core team reveal, return EXACTLY the string "null" and nothing else.

If it is an UPCOMING event, extract ONLY the following details and return them as a valid JSON object:
- "title": The event name. Be concise and specific (e.g. "HackRevolution 2026").
- "event_date": The actual date the EVENT will HAPPEN, in YYYY-MM-DD format.
- "event_time": Start time (e.g. "10:00 AM"). null if not found.
- "venue": Specific location (e.g. "Seminar Hall Block A"). If not found → "MJCET Campus".
- "category": Exactly one of: Technical, Cultural, Sports, Seminar, Workshop, Other.
- "registration_link": Any URL for registration. null if not found.
- "last_register_date": The LAST DATE to register / registration deadline, in YYYY-MM-DD format.
  * Look for: "Register by", "Deadline", "Registration closes".

Caption: {caption}

Return ONLY raw JSON. No markdown. No explanation.
"""

    # ── Attempt with key rotation ───────────────────────────────────
    # Free tier limits (Gemini 2.5 Flash): 15 RPM, 100-250 RPD per project.
    # NOTE: Keys from the SAME Google project share RPD! Use different accounts
    # for each key to get independent RPD pools.
    # 5s delay → 12 req/min → safely below 15 RPM limit.
    CALL_DELAY_SEC = 5        # 12 req/min (safely under 15 RPM free tier)
    RATE_LIMIT_WAIT = 65      # full 60s window + 5s buffer

    max_total_attempts = len(ALL_KEYS) * 3
    for attempt in range(max_total_attempts):
        try:
            if attempt > 0:
                time.sleep(CALL_DELAY_SEC)   # pace requests

            response = _active_model.generate_content([prompt, img])
            text = response.text.strip()

            # ── Parse JSON ──────────────────────────────────────────
            if text.lower() == "null":
                return None
                
            if text.startswith("```"):
                lines = text.splitlines()
                text = "\n".join(lines[1:-1]) if lines[0].startswith("```") else \
                    text.replace("```json", "").replace("```", "")
            text = text.strip()
            
            try:
                details = json.loads(text)
                if not details: return None
                print(f"[GEMINI] ✅ Key #{_current_key_idx + 1} | {details.get('title')} | "
                      f"Date: {details.get('event_date')} | Deadline: {details.get('last_register_date')} | Cat: {details.get('category')}")
                return details
            except:
                return None

        except Exception as e:
            err = str(e)
            if "429" in err:
                print(f"[GEMINI] ⚠️  Key #{_current_key_idx + 1} quota hit (attempt {attempt+1}).")
                switched = _switch_to_next_key()
                if switched:
                    print(f"[GEMINI] → Switched to key #{_current_key_idx + 1}, retrying...")
                    continue
                else:
                    # All keys exhausted — wait full rate-limit window
                    print(f"[GEMINI] All {len(ALL_KEYS)} keys exhausted. "
                          f"Waiting {RATE_LIMIT_WAIT}s for rate-limit window to reset...")
                    time.sleep(RATE_LIMIT_WAIT)
                    _make_model(0, _active_model_name)  # reset to key #1
                    continue
            elif "json" in err.lower() or isinstance(e, json.JSONDecodeError):
                print(f"[GEMINI] JSON parse error. Raw: {str(e)[:100]}")
                return None
            else:
                print(f"[GEMINI ERROR] {err[:200]}")
                return None

    print("[GEMINI] ❌ All retry attempts failed.")
    return None


if __name__ == "__main__":
    # Quick self-test
    images_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "images")
    if os.path.exists(images_dir):
        test_img = next(
            (os.path.join(images_dir, f) for f in os.listdir(images_dir)
             if f.endswith(('.jpg', '.png'))), None
        )
        if test_img:
            print(f"Testing with: {os.path.basename(test_img)}")
            result = refine_event_with_gemini(
                test_img,
                "Join us for a Technical Workshop! Register at forms.google.com/xyz. Date: March 15, Venue: Seminar Hall."
            )
            print(f"Result: {result}")
