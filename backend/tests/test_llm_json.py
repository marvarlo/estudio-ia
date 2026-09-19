import json

import pytest

from app.adapters.outbound.storage.llm_json import extract_json


def test_extracts_raw_json():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extracts_json_from_code_fence():
    text = 'Aca esta:\n```json\n{"a": 1, "b": [1, 2]}\n```\nEso es todo.'
    assert extract_json(text) == {"a": 1, "b": [1, 2]}


def test_extracts_first_balanced_object_without_fence():
    text = 'Claro, aca va: {"a": {"nested": true}, "b": 2} -- espero que ayude.'
    assert extract_json(text) == {"a": {"nested": True}, "b": 2}


def test_extracts_array():
    text = "```\n[1, 2, 3]\n```"
    assert extract_json(text) == [1, 2, 3]


def test_raises_on_unparseable_text():
    with pytest.raises(json.JSONDecodeError):
        extract_json("esto no tiene ningun json adentro")
