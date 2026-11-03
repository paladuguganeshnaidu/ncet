"""NVIDIA provider selection, private credentials, and grounded AI report regressions."""
import json

import pytest
from cryptography.fernet import Fernet

from app.ai_gateway import NVIDIA_DEFAULT_MODEL, NVIDIA_URL, Provider, review_json, select_provider
from app.database import DBSession, IntegrationSetting
from app.verification import AIItem, AIResponse, Extracted, Rule, build_report, evidence_supported


def test_nvidia_environment_key_has_priority(monkeypatch):
    monkeypatch.setenv('NVIDIA_API_KEY', 'nvidia-unit-test-placeholder')
    monkeypatch.setenv('NVIDIA_MODEL', 'meta/llama-3.1-70b-instruct')
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'deepseek-legacy-test-placeholder')
    monkeypatch.setenv('OPENROUTER_API_KEY', 'openrouter-legacy-test-placeholder')
    with DBSession() as db:
        provider = select_provider(db)
    assert provider.name == 'NVIDIA NIM'
    assert provider.url == NVIDIA_URL
    assert provider.model == 'meta/llama-3.1-70b-instruct'
    assert provider.key == 'nvidia-unit-test-placeholder'


def test_admin_can_rotate_nvidia_key_without_exposing_it(client, login, monkeypatch):
    monkeypatch.delenv('NVIDIA_API_KEY', raising=False)
    monkeypatch.setenv('SETTINGS_ENCRYPTION_KEY', Fernet.generate_key().decode())
    secret = 'nvapi-unit-test-private-credential'
    assert client.get('/api/admin/integrations').status_code == 401
    token = login(client, 'admin')
    response = client.put('/api/admin/integrations/nvidia',
                          headers={'X-CSRF-Token': token}, json={'api_key': secret})
    assert response.status_code == 200, response.text
    status = client.get('/api/admin/integrations').json()
    assert status['nvidia_configured']
    assert status['provider'] == 'NVIDIA NIM'
    assert secret not in json.dumps(status)
    with DBSession() as db:
        row = db.get(IntegrationSetting, 'nvidia_key')
        assert row is not None
        assert secret not in row.encrypted_value
    deleted = client.delete('/api/admin/integrations/nvidia',
                            headers={'X-CSRF-Token': token})
    assert deleted.status_code == 200
    with DBSession() as db:
        assert db.get(IntegrationSetting, 'nvidia_key') is None


def test_nvidia_request_uses_fixed_server_endpoint_and_validates_json(monkeypatch):
    requests = []

    class FakeResponse:
        status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return {'choices': [{'message': {'content': '{"summary":"Review requires a HOD","evaluations":[]}'}}]}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            assert kwargs['follow_redirects'] is False
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def post(self, url, *, headers, json):
            requests.append((url, headers, json))
            return FakeResponse()

    monkeypatch.setattr('app.ai_gateway.httpx.Client', FakeClient)
    provider = Provider('NVIDIA NIM', 'meta/llama-3.1-70b-instruct', NVIDIA_URL, 'never-real-secret')
    report = review_json(provider, 'Institutional reviewer.', {'document': 'Untrusted content'})
    assert report['summary'] == 'Review requires a HOD'
    assert len(requests) == 1
    url, headers, body = requests[0]
    assert url == NVIDIA_URL
    assert headers['Authorization'] == 'Bearer never-real-secret'
    assert body['model'] == provider.model
    assert 'response_format' not in body
    assert body['stream'] is False
    assert body['messages'][1]['role'] == 'user'



def test_nemotron_hosted_json_request_disables_streaming_and_reasoning(monkeypatch):
    captured = []

    class FakeResponse:
        status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return {'choices': [{'message': {'content': '{"summary":"Clear", "recommendations":[]}'}}]}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def post(self, url, *, headers, json):
            captured.append(json)
            return FakeResponse()

    monkeypatch.setattr('app.ai_gateway.httpx.Client', FakeClient)
    provider = Provider('NVIDIA NIM', NVIDIA_DEFAULT_MODEL, NVIDIA_URL, 'synthetic-key')
    response = review_json(provider, 'Return JSON.', {'task_total': 1}, max_tokens=950)
    assert response['summary'] == 'Clear'
    body = captured[0]
    assert body['stream'] is False
    assert body['reasoning_effort'] == 'none'
    assert body['temperature'] == 1.0
    assert body['top_p'] == 0.95

    lightning = Provider('NVIDIA NIM', 'nvidia/nemotron-3.5-lightning-30b-a3b',
                         NVIDIA_URL, 'synthetic-key')
    response = review_json(lightning, 'Return JSON.', {'task_total': 1}, max_tokens=950)
    assert response['summary'] == 'Clear'
    lightning_body = captured[1]
    assert lightning_body['stream'] is False
    assert lightning_body['temperature'] == 1.0
    assert lightning_body['top_p'] == 0.95
    assert lightning_body['chat_template_kwargs']['enable_thinking'] is False
    assert 'reasoning_effort' not in lightning_body

def test_ungrounded_ai_pass_is_manual_review(monkeypatch):
    from app import verification
    rule = Rule(id='grammar', title='Clear grammar', type='grammar', required=True)
    extracted = Extracted(['Real report text. Clear objectives and measurable outcomes.'], 1, False, [])
    monkeypatch.setattr(verification, 'call_ai',
                        lambda *_: AIResponse(summary='Looks good', evaluations=[
                            AIItem(rule_id='grammar', result='pass', location='Page 1',
                                   evidence='Invented quotation not in the file',
                                   confidence=.99)]))
    report = build_report(extracted, [rule], 'test-only-key')
    assert report['status'] == 'manual_review'
    assert report['findings'][0]['result'] == 'uncertain'
    assert report['findings'][0]['confidence'] == 0
    assert report['authorship_status'] == 'not_determinable_from_document'
    assert evidence_supported(extracted.pages, 'Clear objectives and measurable outcomes')
    assert not evidence_supported(extracted.pages, 'Fabricated source evidence')


def test_bad_nvidia_json_is_rejected(monkeypatch):
    class FakeResponse:
        status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return {'choices': [{'message': {'content': '{"summary":'}}]}
    class FakeClient:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def post(self, *args, **kwargs): return FakeResponse()
    monkeypatch.setattr('app.ai_gateway.httpx.Client', FakeClient)
    provider = Provider('NVIDIA NIM', 'meta/llama-3.1-70b-instruct', NVIDIA_URL, 'fake-key')
    with pytest.raises(json.JSONDecodeError):
        review_json(provider, 'Reviewer', {'document': 'Text'})
