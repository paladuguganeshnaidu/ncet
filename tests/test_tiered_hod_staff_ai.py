"""Three complexity tiers of the HOD -> staff -> AI -> HOD review lifecycle.

All reports are synthetic and the model is stubbed: this is a deterministic
integration regression, not a paid NVIDIA request or evidence about authorship.
"""
from fastapi.testclient import TestClient

from app.ai_gateway import Provider
from app.database import DBSession, User
from app.main import app
from app.taskflow import run_task_once
from app.verification import Extracted

PDF = b'%PDF-1.7\n1 0 obj<</Type/Catalog>>endobj\n%%EOF'
LEVELS = {'easy': (2, 2, 100, 'awaiting_hod'),
          'medium': (4, 3, 75, 'correction_required'),
          'hard': (6, 4, 67, 'correction_required')}


def _rules(level, count):
    return [
        {'id': f'{level}_requirement_{index}', 'title': f'{level.title()} requirement {index + 1}',
         'type': 'other', 'required': False, 'value': '',
         'instructions': f'Check the documented {level} evidence for item {index + 1}.'}
        for index in range(count)
    ]


def test_three_level_hod_staff_ai_human_review(client, login, monkeypatch):
    from app import taskflow

    hod_csrf = login(client, 'hod')
    uploaded = client.post(
        '/api/tasks/batches',
        headers={'X-CSRF-Token': hod_csrf},
        data={'title': 'TEST ONLY: easy, medium and hard evidence assignments'},
        files=[
            ('files', (f'test-only-{level}-reference.pdf', PDF, 'application/pdf'))
            for level in LEVELS
        ],
    )
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()['count'] == 3

    listed = client.get('/api/tasks').json()['items']
    tasks = {level: next(item for item in listed if item['file'] ==
                         f'test-only-{level}-reference.pdf') for level in LEVELS}
    with DBSession() as db:
        staff_id = db.query(User).filter(User.username == 'staff').one().id

    assigned = client.post(
        '/api/tasks/assign',
        headers={'X-CSRF-Token': hod_csrf},
        json={
            'task_ids': [item['id'] for item in tasks.values()],
            'staff_id': staff_id,
            'notes': 'TEST ONLY. Staff must follow the HOD reference document and evidence checklist.',
            'rules_by_task': {
                str(item['id']): _rules(level, LEVELS[level][0])
                for level, item in tasks.items()
            },
        },
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()['assigned'] == 3

    monkeypatch.setattr(taskflow, 'select_provider',
        lambda db: Provider('NVIDIA', 'mock-tiered-model',
                            'https://integrate.api.nvidia.com/v1/chat/completions', 'unit-test-only'))
    monkeypatch.setattr('app.verification.extract_document',
        lambda filename, data: Extracted(
            ['Academic Report. TEST ONLY. Supporting evidence for each assigned item.'],
            1, False, []))

    calls = []
    def simulated_model(provider, system, payload, max_tokens=2200):
        requirements = payload['rules']
        count = len(requirements)
        passed = {v[0]: v[1] for v in LEVELS.values()}[count]
        calls.append(count)
        return {
            'summary': f'Synthetic {count}-rule review completed; HOD decides final approval.',
            'evaluations': [{
                'rule_id': rule['id'],
                'result': 'pass' if index < passed else 'issue',
                'confidence': 0.98,
                'evidence': 'Academic Report',
                'issue': '' if index < passed else 'Item needs further evidence.',
                'correction': '' if index < passed else 'Supply the missing evidence.',
            } for index, rule in enumerate(requirements)],
        }
    monkeypatch.setattr(taskflow, 'review_json', simulated_model)

    with TestClient(app) as staff:
        staff_csrf = login(staff, 'staff')
        inbox = staff.get('/api/tasks/notifications/inbox')
        assert inbox.status_code == 200
        assert inbox.json()['unread'] == 3
        assert len(staff.get('/api/tasks').json()['items']) == 3
        for level, item in tasks.items():
            reference = staff.get(f"/api/tasks/{item['id']}/reference")
            assert reference.status_code == 200
            response = staff.post(
                f"/api/tasks/{item['id']}/submit",
                headers={'X-CSRF-Token': staff_csrf},
                files={'file': (f'test-only-{level}-completed.pdf', PDF, 'application/pdf')},
            )
            assert response.status_code == 201, (level, response.text)
            assert run_task_once(), level

        staff_results = {item['id']: item for item in staff.get('/api/tasks').json()['items']}
        for level, item in tasks.items():
            _, _, expected_score, expected_state = LEVELS[level]
            result = staff_results[item['id']]
            assert result['score'] == expected_score, (level, result)
            assert result['state'] == expected_state, (level, result)
            assert result['report']['ai_used']
            assert result['report']['authorship_status'] == 'not_determinable_from_document'
            assert result['report']['reference_comparison']['available']
            assert len(result['report']['findings']) == LEVELS[level][0]

        assert sorted(calls) == [2, 4, 6]
        easy = tasks['easy']['id']
        approved = client.post(
            f'/api/tasks/{easy}/decide',
            headers={'X-CSRF-Token': hod_csrf},
            json={'decision': 'approved',
                  'note': 'HOD independently verified the synthetic easy assignment.'},
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()['state'] == 'approved'
        assert next(item for item in staff.get('/api/tasks').json()['items']
                    if item['id'] == easy)['state'] == 'approved'
