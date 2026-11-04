"""Bounded, evidence-first academic document signals and weighted checklist scoring.

These metrics describe content and checklist completion. They never infer human
authorship, plagiarism, misconduct, or factual correctness from a similarity score.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Iterable

MAX_COMPARISON_TOKENS = 8_000
SHINGLE_WORDS = 5
MAX_REFERENCE_PROMPT_CHARS = 12_000

_WORDS = re.compile(r"\b[\w]+(?:[-'][\w]+)*\b", flags=re.UNICODE)
_CITATIONS = re.compile(
    r"(?:\[\s*\d+(?:\s*[-,]\s*\d+)*\s*\]|\bdoi:\s*10\.\d{4,9}/\S+|"
    r"\([A-Za-z][A-Za-z.' -]{1,45},\s*(?:19|20)\d{2}[a-z]?\))",
    flags=re.IGNORECASE,
)


def word_count(text: str) -> int:
    return len(_WORDS.findall(text))


def evidence_passages(extracted: Any, max_chars: int = 20_000) -> list[dict[str, Any]]:
    """Bounded, verbatim submission passages the model can cite by identifier."""
    passages = []
    used = 0
    for page_number, page in enumerate(getattr(extracted, 'pages', []) or [], 1):
        text = ' '.join(page.split())
        while text and len(passages) < 80 and used < max_chars:
            end = min(len(text), 240, max_chars - used)
            if end < len(text):
                boundary = text.rfind(' ', 0, end)
                if boundary >= 40:
                    end = boundary
            quote = text[:end].strip()
            if len(quote) < 10:
                break
            passages.append({'id': f'e{len(passages) + 1}', 'page': page_number, 'text': quote})
            used += len(quote)
            text = text[end:].lstrip()
    return passages


def document_signals(extracted: Any) -> dict[str, Any]:
    """Report descriptive metrics, not truth or originality verdicts."""
    text = '\n'.join(getattr(extracted, 'pages', []) or [])
    citations = _CITATIONS.findall(text)
    return {
        'page_count': int(getattr(extracted, 'page_count', 0) or 0),
        'word_count': word_count(text),
        'character_count': len(text),
        'citation_markers': len(citations),
        'citation_status': 'markers_detected' if citations else 'not_detected',
        'text_extraction_limited': bool(getattr(extracted, 'needs_ocr_review', True)),
        'notes': list(getattr(extracted, 'notes', []) or [])[:20],
    }


def _shingles(text: str) -> set[str]:
    tokens = [token.casefold() for token in _WORDS.findall(text)[:MAX_COMPARISON_TOKENS]]
    if len(tokens) < SHINGLE_WORDS:
        return set()
    return {' '.join(tokens[i:i + SHINGLE_WORDS])
            for i in range(len(tokens) - SHINGLE_WORDS + 1)}


def reference_comparison(reference: Any | None, submitted: Any,
                         reference_data: bytes | None = None) -> dict[str, Any]:
    """Compare observable text overlap without making plagiarism allegations."""
    report = {
        'available': False,
        'overlap_percent': None,
        'reference_sha256': hashlib.sha256(reference_data).hexdigest() if reference_data else None,
        'comparison_limit_tokens': MAX_COMPARISON_TOKENS,
        'note': 'Reference overlap is informational. Templates may legitimately share text.',
    }
    if reference is None or getattr(reference, 'needs_ocr_review', True):
        report['reason'] = 'Reference text could not be reliably extracted.'
        return report
    source = '\n'.join(getattr(reference, 'pages', []) or [])
    target = '\n'.join(getattr(submitted, 'pages', []) or [])
    src = _shingles(source)
    dst = _shingles(target)
    if not src or not dst:
        report['reason'] = 'Not enough readable words for a comparison.'
        return report
    report['available'] = True
    report['overlap_percent'] = round(100 * len(src & dst) / len(dst), 1)
    report['reference_words_analyzed'] = min(word_count(source), MAX_COMPARISON_TOKENS)
    report['submission_words_analyzed'] = min(word_count(target), MAX_COMPARISON_TOKENS)
    report['truncated_for_comparison'] = (
        word_count(source) > MAX_COMPARISON_TOKENS
        or word_count(target) > MAX_COMPARISON_TOKENS
    )
    return report


def reference_prompt_excerpt(reference: Any | None) -> str:
    if reference is None or getattr(reference, 'needs_ocr_review', True):
        return ''
    text = '\n\n'.join(
        f'[REFERENCE PAGE {i + 1}]\n{page}'
        for i, page in enumerate(getattr(reference, 'pages', []) or [])
    )
    return text[:MAX_REFERENCE_PROMPT_CHARS]


def weighted_rubric(rules: Iterable[Any], findings: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Relative rule weights; unverified required checks prevent a final score."""
    rules = list(rules)
    total = sum(int(getattr(rule, 'weight', 1)) for rule in rules)
    earned = 0
    assessed = 0
    mandatory_failed = []
    unresolved = []
    for rule in rules:
        rule_id = rule.id
        weight = int(getattr(rule, 'weight', 1))
        item = findings.get(rule_id)
        status = item.get('result') if item else 'uncertain'
        if status in ('pass', 'issue'):
            assessed += weight
        else:
            unresolved.append(rule_id)
        if status == 'pass':
            earned += weight
        if status == 'issue' and rule.required:
            mandatory_failed.append(rule_id)
    complete = bool(rules) and not unresolved
    return {
        'score': round(100 * earned / total) if total and complete else None,
        'coverage_percent': round(100 * assessed / total, 1) if total else 0.0,
        'earned_weight': earned,
        'assessed_weight': assessed,
        'total_weight': total,
        'mandatory_failed': mandatory_failed,
        'unresolved': unresolved,
        'scale': 'relative_checklist_weights',
        'scope': 'Document adherence and evidence, not human authorship.',
    }
