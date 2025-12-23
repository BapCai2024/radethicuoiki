from __future__ import annotations
import json
import requests

class AIError(Exception):
    pass

def openai_compatible_generate(base_url: str, api_key: str, model: str, prompt: str, timeout: int = 45) -> str:
    if not api_key:
        raise AIError("Chưa có API key.")
    base_url = (base_url or "https://api.openai.com").rstrip("/")
    url = f"{base_url}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Bạn là chuyên gia ra đề tiểu học theo CTGDPT 2018 và TT27. Trả lời đúng yêu cầu."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
    }
    try:
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout)
    except Exception as e:
        raise AIError(f"Lỗi mạng: {e}")
    if r.status_code >= 400:
        raise AIError(f"API lỗi {r.status_code}: {r.text[:300]}")
    try:
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        raise AIError("Không parse được phản hồi API.")

def gemini_ai_studio_generate(api_key: str, model: str, prompt: str, timeout: int = 45) -> str:
    if not api_key:
        raise AIError("Chưa có API key.")
    model = model or "gemini-1.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.4}}
    try:
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout)
    except Exception as e:
        raise AIError(f"Lỗi mạng: {e}")
    if r.status_code >= 400:
        raise AIError(f"Gemini lỗi {r.status_code}: {r.text[:300]}")
    try:
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        raise AIError("Không parse được phản hồi Gemini.")
