"""Evidence-grade document signals: descriptive, bounded and backward-compatible."""
from dataclasses import dataclass

from app.document_intelligence import (
    MAX_COMPARISON_TOKENS, document_signals, reference_comparison,
    reference_prompt_excerpt, weighted_rubric, word_count,
)
from app.verification import Rule, Extracted, deterministic


def test_weighted_rubric_uses_importance_not_rule_count():
    rules = [
        Rule(id='core', title='Mandatory objective', type='other', weight=5, required=True),
        Rule(id='minor', title='Optional appendix', type='other', weight=1, required=False),
    ]
    failed = {'core': {'result': 'issue'}, 'minor': {'result': 'pass'}}
    report = weighted_rubric(rules, failed)
    assert report['score'] == 17
    assert report['mandatory_failed'] == ['core']
    assert report['coverage_percent'] == 100
    assert report['total_weight'] == 6
    assert weighted_rubric(rules, {'minor': {'result': 'pass'}})['score'] is None
    assert weighted_rubric(rules, {'minor': {'result': 'pass'}})['unresolved'] == ['core']


def test_old_checklists_default_to_equal_weights():
    rules = [
        Rule.model_validate({'id': 'first', 'title': 'First check', 'type': 'other'}),
        Rule.model_validate({'id': 'second', 'title': 'Second check', 'type': 'other'}),
    ]
    result = weighted_rubric(rules, {'first': {'result': 'pass'}, 'second': {'result': 'issue'}})
    assert result['score'] == 50 and result['total_weight'] == 2


def test_word_limits_are_deterministic_and_do_not_fake_confidence_on_ocr():
    rules = [
        Rule(id='minimum', title='At least four words', type='min_words', value='4'),
        Rule(id='maximum', title='No more than five words', type='max_words', value='5'),
    ]
    results, _ = deterministic(rules, Extracted(['One two three four'], 1, False, []))
    assert [item['result'] for item in results] == ['pass', 'pass']
    results, _ = deterministic(rules, Extracted(['One two three'], 1, False, []))
    assert results[0]['result'] == 'issue'
    results, _ = deterministic(rules, Extracted(['One two three'], 1, True, []))
    assert results[0]['result'] == 'uncertain'
    assert word_count('One two-three four') == 3


def test_reference_overlap_is_bounded_and_does_not_assert_plagiarism():
    reference = Extracted(['The college quality assurance report includes a department overview.'], 1, False, [])
    submitted = Extracted(['The college quality assurance report includes a department overview and evidence.'], 1, False, [])
    comparison = reference_comparison(reference, submitted, b'reference bytes')
    assert comparison['available']
    assert comparison['overlap_percent'] > 0
    assert comparison['reference_sha256']
    assert 'informational' in comparison['note']
    assert reference_prompt_excerpt(reference).startswith('[REFERENCE PAGE 1]')
    assert reference_comparison(None, submitted)['available'] is False
    huge = Extracted(['token ' * (MAX_COMPARISON_TOKENS + 100)], 1, False, [])
    bounded = reference_comparison(huge, huge)
    assert bounded['truncated_for_comparison']
    assert bounded['reference_words_analyzed'] == MAX_COMPARISON_TOKENS


def test_document_signals_are_descriptive_not_authorship_predictions():
    extracted = Extracted(['Sentence one [1].\nSmith, 2020 DOI:10.1000/xyz'], 2, False, [])
    signals = document_signals(extracted)
    assert signals['page_count'] == 2
    assert signals['citation_markers'] >= 2
    assert signals['word_count'] > 0
    assert 'human_score' not in signals and 'plagiarism_score' not in signals

def test_submission_passages_are_verbatim_bounded_and_page_scoped():
    from app.document_intelligence import evidence_passages
    from app.verification import evidence_supported
    extracted=Extracted(['Source evidence on page one. '*40,'Second page evidence with a different detail.'],2,False,[])
    passages=evidence_passages(extracted,max_chars=500)
    assert passages and sum(len(item['text']) for item in passages)<=500
    assert all(len(item['text'])<=240 for item in passages)
    assert all(evidence_supported([extracted.pages[item['page']-1]],item['text']) for item in passages)
    assert len({item['id'] for item in passages})==len(passages)
    assert evidence_passages(extracted,max_chars=0)==[]
