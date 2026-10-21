"""DeepSeek document evaluation with secure, configurable transport.

A direct DeepSeek API key takes precedence. The existing encrypted OpenRouter
key can route DeepSeek when a dedicated key has not yet been provisioned.
Never silently substitute another model.
"""
import json
import os
import re
from dataclasses import dataclass

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from .database import IntegrationSetting


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
    master = os.getenv('SETTINGS_ENCRYPTION_KEY')
    direct = _decrypt(db.get(IntegrationSetting, 'deepseek_key'), master) or os.getenv('DEEPSEEK_API_KEY')
    if direct:
        return Provider('DeepSeek', os.getenv('DEEPSEEK_MODEL', 'deepseek-flash'),
                        'https://api.deepseek.com/chat/completions', direct)
    router = _decrypt(db.get(IntegrationSetting, 'openrouter_key'), master) or os.getenv('OPENROUTER_API_KEY')
    if router:
        return Provider('OpenRouter · DeepSeek', os.getenv('OPENROUTER_DEEPSEEK_MODEL','deepseek/deepseek-v3.2'),
                        'https://openrouter.ai/api/v1/chat/completions', router)
    return None


def review_json(provider: Provider, system: str, payload: dict, *, max_tokens: int = 2200):
    """Only trusted server constants define API URLs; document text stays data."""
    body = {'model':provider.model,'max_tokens':max_tokens,'temperature':0,
            'response_format':{'type':'json_object'},
            'messages':[{'role':'system','content':system+' Respond using only a valid JSON object.'},
                        {'role':'user','content':json.dumps(payload,ensure_ascii=False)}]}
    headers={'Authorization':'Bearer '+provider.key,'Content-Type':'application/json'}
    with httpx.Client(timeout=httpx.Timeout(95.0,connect=12.0),follow_redirects=False) as client:
        response=client.post(provider.url,headers=headers,json=body)
        response.raise_for_status()
        raw=response.json()['choices'][0]['message']['content']
    if not isinstance(raw,str):raise ValueError('AI response was not JSON text.')
    text=raw.strip()
    if text.startswith('```'):
        text=re.sub(r'^```(?:json)?\s*|\s*```$','',text,flags=re.I)
    if len(text)>100_000:raise ValueError('AI response is too large.')
    obj=json.loads(text)
    if not isinstance(obj,dict):raise ValueError('AI response is not a JSON object.')
    return obj
