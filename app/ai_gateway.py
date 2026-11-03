"""Server-side AI gateway for NVIDIA NIM and explicitly configured legacy providers.

Provider URLs are fixed server constants. Uploaded document text is untrusted data;
an unavailable model or malformed response must never become a fabricated pass.
"""
import json
import os
import re
import time
from dataclasses import dataclass

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from .database import IntegrationSetting

NVIDIA_URL = 'https://integrate.api.nvidia.com/v1/chat/completions'
NVIDIA_DEFAULT_MODEL = 'meta/llama-3.1-70b-instruct'


@dataclass(frozen=True)
class Provider:
    name: str
    model: str
    url: str
    key: str


def _decrypt(setting, master):
    if not setting or not master:
        return None
    try:
        return Fernet(master.encode()).decrypt(setting.encrypted_value.encode()).decode()
    except (ValueError, InvalidToken):
        return None


def select_provider(db: Session) -> Provider | None:
    """NVIDIA takes priority; never switch provider after an API error.

    Existing DeepSeek and OpenRouter credentials remain usable only when NVIDIA
    is not configured, preventing a surprise migration outage for current users.
    """
    master = os.getenv('SETTINGS_ENCRYPTION_KEY')
    nvidia = _decrypt(db.get(IntegrationSetting, 'nvidia_key'), master) or os.getenv('NVIDIA_API_KEY')
    if nvidia:
        return Provider('NVIDIA NIM', os.getenv('NVIDIA_MODEL') or NVIDIA_DEFAULT_MODEL,
                        NVIDIA_URL, nvidia)
    direct = _decrypt(db.get(IntegrationSetting, 'deepseek_key'), master) or os.getenv('DEEPSEEK_API_KEY')
    if direct:
        return Provider('DeepSeek', os.getenv('DEEPSEEK_MODEL', 'deepseek-flash'),
                        'https://api.deepseek.com/chat/completions', direct)
    router = _decrypt(db.get(IntegrationSetting, 'openrouter_key'), master) or os.getenv('OPENROUTER_API_KEY')
    if router:
        return Provider('OpenRouter · DeepSeek',
                        os.getenv('OPENROUTER_DEEPSEEK_MODEL', 'deepseek/deepseek-v3.2'),
                        'https://openrouter.ai/api/v1/chat/completions', router)
    return None


def review_json(provider: Provider, system: str, payload: dict, *, max_tokens: int = 2200):
    """Request strict JSON text; independently parse and validate the result.

    NVIDIA's catalog models differ in their support for response_format, so
    avoid sending that optional argument to NVIDIA NIM.
    """
    body = {
        'model': provider.model,
        'max_tokens': max_tokens,
        'temperature': 0,
        'messages': [
            {'role': 'system', 'content': system + ' Respond using only one valid JSON object.'},
            {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)},
        ],
    }
    if provider.url != NVIDIA_URL:
        body['response_format'] = {'type': 'json_object'}
    headers = {'Authorization': 'Bearer ' + provider.key, 'Content-Type': 'application/json'}
    with httpx.Client(timeout=httpx.Timeout(95.0, connect=12.0),
                      follow_redirects=False) as client:
        for attempt in range(2):
            try:
                response = client.post(provider.url, headers=headers, json=body)
                if response.status_code in (429, 500, 502, 503, 504) and attempt == 0:
                    time.sleep(1)
                    continue
                response.raise_for_status()
                break
            except httpx.TransportError:
                if attempt:
                    raise
                time.sleep(1)
    choices = response.json().get('choices', [])
    if not choices or not isinstance(choices[0], dict):
        raise ValueError('AI response has no completion choice.')
    message = choices[0].get('message') or {}
    raw = message.get('content') if isinstance(message, dict) else None
    if isinstance(raw, list):
        raw = ''.join(chunk.get('text', '') for chunk in raw if isinstance(chunk, dict))
    if not isinstance(raw, str):
        raise ValueError('AI response was not JSON text.')
    content = raw.strip()
    if content.startswith(chr(96) * 3):
        content = re.sub(r'^\x60{3}(?:json)?\s*|\s*\x60{3}$', '', content, flags=re.I).strip()
    if len(content) > 100_000:
        raise ValueError('AI response is too large.')
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError('AI response is not a JSON object.')
    return parsed
