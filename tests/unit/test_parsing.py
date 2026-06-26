"""Unit tests for JSON parsing utilities."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from memorule.exceptions import PolicyParseError
from memorule.prompts.parsing import extract_json, parse_llm_response
from memorule.prompts.templates import ExtractionResponse, ReconciliationResponse


class _Resp(BaseModel):
    action: str
    score: float


def test_extract_plain_json():
    assert extract_json('{"a": 1}') == '{"a": 1}'


def test_extract_fenced_json():
    text = "Here:\n```json\n{\"a\": 1}\n```\nDone"
    assert extract_json(text) == '{"a": 1}'


def test_extract_fenced_no_lang():
    text = "```\n{\"a\": 1}\n```"
    assert extract_json(text) == '{"a": 1}'


def test_extract_embedded_object():
    text = 'Sure, the answer is {"a": 1} okay'
    assert extract_json(text) == '{"a": 1}'


def test_parse_valid():
    resp = parse_llm_response('{"action": "merge", "score": 0.9}', _Resp, stage="t")
    assert resp.action == "merge"
    assert resp.score == 0.9


def test_parse_invalid_json_raises():
    with pytest.raises(PolicyParseError) as exc:
        parse_llm_response("not json", _Resp, stage="t")
    assert exc.value.stage == "t"
    assert exc.value.raw_output == "not json"


def test_parse_schema_mismatch_raises():
    with pytest.raises(PolicyParseError):
        parse_llm_response('{"action": "merge"}', _Resp, stage="t")


def test_parse_extraction_coerces_dict_content():
    raw = (
        '{"type": "preference", "content": {"likes": ["grilled"], "dislikes": ["soup"]}, '
        '"summary": "food", "confidence": 0.9}'
    )
    resp = parse_llm_response(raw, ExtractionResponse, stage="memory_extraction")
    assert resp.type == "preference"
    assert resp.content == '{"likes": ["grilled"], "dislikes": ["soup"]}'
    assert resp.summary == "food"
    assert resp.confidence == 0.9


def test_parse_extraction_preserves_string_content():
    raw = (
        '{"type": "preference", "content": "User likes grilled food and dislikes soup", '
        '"summary": "food", "confidence": 0.9}'
    )
    resp = parse_llm_response(raw, ExtractionResponse, stage="memory_extraction")
    assert resp.content == "User likes grilled food and dislikes soup"


def test_parse_reconciliation_coerces_dict_updated_content():
    raw = (
        '{"action": "update", "reason": "newer info", '
        '"updated_content": {"likes": ["grilled"]}, "updated_summary": null}'
    )
    resp = parse_llm_response(raw, ReconciliationResponse, stage="conflict_resolution")
    assert resp.updated_content == '{"likes": ["grilled"]}'
