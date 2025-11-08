#chatbot_model.py

import os, json, re, mimetypes
from typing import Dict, Any
from langdetect import detect, DetectorFactory
import requests
from PIL import Image
import pytesseract
import textract
import pdfplumber
from docx import Document

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b:free")
APP_NAME = os.getenv("APP_NAME", "AgroBot Chat Assistant")
APP_URL = os.getenv("APP_URL", "http://127.0.0.1:5000")


DetectorFactory.seed = 0

try:
    from googletrans import Translator
    TRANSLATOR = Translator(); HAS_GOOGLETRANS = True
except Exception:
    TRANSLATOR = None; HAS_GOOGLETRANS = False
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') or None
if OPENAI_API_KEY:
    try:
        import openai; openai.api_key = OPENAI_API_KEY; HAS_OPENAI = True
    except Exception:
        HAS_OPENAI = False
else:
    HAS_OPENAI = False
    
KB_PATH = os.path.join(os.path.dirname(__file__), 'kb.json')


def load_kb():
    if not os.path.exists(KB_PATH): return {}
    with open(KB_PATH,'r',encoding='utf-8') as f:
        data = json.load(f)
    out = {}
    if isinstance(data,list):
        for entry in data:
            keys = entry.get('keywords') or []
            if isinstance(keys,str): keys=[k.strip() for k in keys.split(',') if k.strip()]
            for k in keys:
                out[k.lower()] = {'en': entry.get('answer_en',''), 'hi': entry.get('answer_hi',''), 'ta': entry.get('answer_ta',''), 'ka': entry.get('answer_ka',''), 'ma': entry.get('answer_ma',''), 'te': entry.get('answer_te','')}
    elif isinstance(data,dict):
        for k,v in data.items():
            if isinstance(v,str): out[k.lower()] = {'en': v}
            elif isinstance(v,dict): out[k.lower()] = {'en': v.get('answer_en',''), 'hi': v.get('answer_hi',''), 'ta': v.get('answer_ta',''), 'ka': v.get('answer_ka',''), 'ma': v.get('answer_ma',''), 'te': v.get('answer_te','')}
    return out
KB = load_kb()


def detect_language(text: str) -> str:
    try: return detect(text)
    except Exception: return 'en'
    
    
def translate_text(text: str, dest: str) -> str:
    dest = dest[:2]
    if not HAS_GOOGLETRANS: return text
    try: return TRANSLATOR.translate(text, dest=dest).text
    except Exception: return text
    
    
def find_in_kb(message: str):
    m = message.lower()
    for k,v in KB.items():
        if k in m: return v
    tokens = re.findall(r"\w+", m)
    for k,v in KB.items():
        ktoks = re.findall(r"\w+", k)
        if any(t in ktoks for t in tokens if len(t)>3): return v
    return None


# def openai_fallback(user_profile: Dict[str,Any], message_text: str, target_lang: str='en') -> str:
#     if not HAS_OPENAI: return ''
#     try:
#         prompt = f"You are an expert agronomist. User profile: {user_profile}\nQuestion: {message_text}\nAnswer concisely."
#         resp = openai.ChatCompletion.create(model='gpt-4o-mini', messages=[{'role':'system','content':'You are an agronomist.'},{'role':'user','content':prompt}], max_tokens=300)
#         text = resp['choices'][0]['message']['content'].strip()
#         if target_lang and target_lang!='en' and HAS_GOOGLETRANS: text = translate_text(text, target_lang)
#         return text
#     except Exception:
#         return ''
    

def openrouter_fallback(user_profile: Dict[str, Any], message_text: str, target_lang: str = 'en') -> str:
    """
    Use OpenRouter API to get AI-generated responses when not found in KB.
    """
    if not OPENROUTER_API_KEY:
        return ''

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": APP_URL,
        "X-Title": APP_NAME,
        "Content-Type": "application/json"
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "You are an expert agricultural assistant helping farmers."},
            {"role": "user", "content": f"User profile: {user_profile}\nQuestion: {message_text}\nGive a clear, useful, practical answer."}
        ],
        "max_tokens": 700
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
            if target_lang != "en" and HAS_GOOGLETRANS:
                text = translate_text(text, target_lang)
            return text
        else:
            print("OpenRouter error:", response.status_code, response.text)
            return ''
    except Exception as e:
        print("Error contacting OpenRouter:", e)
        return ''
    

# -------------------- 🔍 FILE ANALYZER --------------------

def analyze_uploaded_file(file_path: str) -> str:
    """
    Analyze an uploaded file (.pdf, .docx, .txt, .csv, .xlsx, .png, .jpg)
    Extract text using textract/pytesseract and generate a summary (max 5000 chars).
    """
    import mimetypes, csv, pandas as pd, pdfplumber
    from PIL import Image
    import pytesseract, textract, traceback

    file_path = os.path.abspath(file_path)
    ext = os.path.splitext(file_path)[1].lower()
    text_content = ""

    try:
        # --- TEXT EXTRACTION BY FILE TYPE ---
        if ext in [".txt"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text_content = f.read()

        elif ext in [".pdf"]:
            try:
                with pdfplumber.open(file_path) as pdf:
                    pages = [page.extract_text() or "" for page in pdf.pages]
                    text_content = "\n".join(pages)
            except Exception:
                text_content = textract.process(file_path).decode("utf-8", errors="ignore")

        elif ext in [".docx"]:
            try:
                doc = Document(file_path)
                text_content = "\n".join(p.text for p in doc.paragraphs)
            except Exception:
                text_content = textract.process(file_path).decode("utf-8", errors="ignore")

        elif ext in [".csv"]:
            try:
                with open(file_path, newline="", encoding="utf-8", errors="ignore") as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    text_content = "\n".join([", ".join(row) for row in rows[:100]])  # limit to first 100 rows
            except Exception:
                text_content = textract.process(file_path).decode("utf-8", errors="ignore")

        elif ext in [".xlsx"]:
            try:
                df = pd.read_excel(file_path)
                text_content = df.to_string(index=False)[:20000]  # limit size
            except Exception:
                text_content = textract.process(file_path).decode("utf-8", errors="ignore")

        elif ext in [".png", ".jpg", ".jpeg"]:
            try:
                img = Image.open(file_path)
                text_content = pytesseract.image_to_string(img)
            except Exception:
                text_content = "Unable to extract text from the image."

        else:
            text_content = textract.process(file_path).decode("utf-8", errors="ignore")

        # --- CLEAN & LIMIT TEXT ---
        text_content = re.sub(r"\s+", " ", text_content or "").strip()
        if not text_content:
            return "No readable text could be extracted from the uploaded file."

        # --- SUMMARIZATION PROMPT ---
        summary_prompt = (
            f"Analyze and summarize the following content in a clear, concise, AI-style manner. "
            f"Limit the result to around 5000 characters. Preserve any important data, entities, or insights.\n\n"
            f"=== FILE CONTENT START ===\n{text_content[:15000]}\n=== FILE CONTENT END ==="
        )

        # --- TRY AI SUMMARIZATION VIA OPENROUTER / OPENAI ---
        summarized_text = ""
        try:
            if OPENROUTER_API_KEY:
                headers = {
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "HTTP-Referer": APP_URL,
                    "X-Title": APP_NAME,
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": "You are an intelligent summarization assistant."},
                        {"role": "user", "content": summary_prompt}
                    ],
                    "max_tokens": 2000
                }
                resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                if resp.status_code == 200:
                    summarized_text = resp.json()["choices"][0]["message"]["content"].strip()

            elif HAS_OPENAI:
                import openai
                resp = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an intelligent summarization assistant."},
                        {"role": "user", "content": summary_prompt},
                    ],
                    max_tokens=2000
                )
                summarized_text = resp["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print("AI summarization error:", e)

        # --- FALLBACK (LOCAL BASIC SUMMARIZER) ---
        if not summarized_text:
            sentences = re.split(r'(?<=[.!?]) +', text_content)
            summarized_text = " ".join(sentences[:20])
            summarized_text = f"📄 Summary (local fallback):\n{summarized_text[:5000]}"

        # Final limit
        return summarized_text[:5000]

    except Exception as e:
        print("❌ analyze_uploaded_file() error:", e)
        traceback.print_exc()
        return "An error occurred while analyzing the uploaded file."


def process_message(user_profile: Dict[str,Any], message_text: str) -> str:
    if not message_text or not message_text.strip(): return 'Please ask a question about crops, soil, or pests.'
    detected = detect_language(message_text)
    if HAS_GOOGLETRANS and detected != 'en':
        try: english_text = translate_text(message_text, 'en')
        except Exception: english_text = message_text
    else:
        english_text = message_text
    kb_item = find_in_kb(english_text)
    if kb_item:
        lang = (user_profile.get('preferred_language') or detected or 'en')[:2]
        ans = kb_item.get(lang) or kb_item.get('en') or next(iter(kb_item.values()), '')
        if not ans and kb_item.get('en') and lang!='en' and HAS_GOOGLETRANS:
            ans = translate_text(kb_item.get('en'), lang)
        return ans
    if HAS_OPENAI:
        resp = openai_fallback(user_profile or {}, english_text, target_lang=(user_profile.get('preferred_language') or detected or 'en')[:2])
        if resp: return resp
    # Try OpenRouter next
    resp = openrouter_fallback(user_profile or {}, english_text, target_lang=(user_profile.get('preferred_language') or detected or 'en')[:2])
    if resp:
        return resp

    return "I don't have that answer in KB. Try asking about a specific crop or pest."
