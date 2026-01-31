import requests
import os
import json

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = "llama3.2"

def generate_summary(text: str) -> str:
    """
    Ollama üzerinden Llama 3.2 modelini kullanarak metin özeti oluşturur.
    """
    if not text or len(text) < 50:
        return "Metin özetlemek için çok kısa."

    prompt = f"""Aşağıdaki metni Türkçeye özetle ve ana maddeleri çıkar:

{text}

Özet:"""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        # Öncelikle modelin varlığını kontrol etmeye gerek yok, pull işlemi server.py içinde veya manuel ele alınabilir.
        # Ancak basitlik için direkt generate endpointine istek atıyoruz.
        # Kullanıcı ilk çalıştırmada `ollama pull llama3.2` yapmalı veya yapılması sağlanmalı.
        response = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result.get("response", "Özet oluşturulamadı.")
    except Exception as e:
        return f"LLM Hatası: {str(e)}"
