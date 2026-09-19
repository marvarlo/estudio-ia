"""Contrato del adaptador contra el endpoint OpenAI-compatible de Lemonade
`/audio/transcriptions` -- payload de respuesta verificado en vivo contra un
audio real (ver README, fase 4): segments[].words[] con start/end/probability."""
from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from app.adapters.outbound.transcription.lemonade_transcription import LemonadeTranscriptionAdapter

FAKE_RESPONSE = {
    "detected_language": "spanish",
    "language": "spanish",
    "duration": 2.5,
    "segments": [
        {
            "text": "Hola mundo",
            "words": [
                {"word": " Hola", "start": 0.0, "end": 0.5, "probability": 0.98},
                {"word": " mundo", "start": 0.5, "end": 1.0, "probability": 0.2},
            ],
        }
    ],
    "text": "Hola mundo",
}


async def test_transcribe_parses_words_and_flags_suspect(tmp_path, monkeypatch):
    audio_path = tmp_path / "clip.mp3"
    audio_path.write_bytes(b"fake-audio")

    captured = {}

    async def fake_post(self, url, data=None, files=None):
        captured["url"] = url
        captured["data"] = data
        captured["files"] = files
        request = httpx.Request("POST", url)
        return httpx.Response(200, json=FAKE_RESPONSE, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    adapter = LemonadeTranscriptionAdapter("http://localhost:13305/api/v1")
    result = await adapter.transcribe(audio_path)

    assert captured["url"] == "http://localhost:13305/api/v1/audio/transcriptions"
    assert captured["data"]["model"] == "Whisper-Large-v3-Turbo"
    assert captured["data"]["response_format"] == "verbose_json"
    assert "file" in captured["files"]

    assert result.language == "spanish"
    assert result.raw_text == "Hola mundo"
    assert len(result.words) == 2
    assert result.words[0].text == "Hola"
    assert result.words[0].suspect is False
    assert result.words[1].text == "mundo"
    assert result.words[1].suspect is True  # probability 0.2 < 0.35


async def test_transcribe_passes_language_when_given(tmp_path, monkeypatch):
    audio_path = tmp_path / "clip.mp3"
    audio_path.write_bytes(b"x")
    captured = {}

    async def fake_post(self, url, data=None, files=None):
        captured["data"] = data
        request = httpx.Request("POST", url)
        return httpx.Response(200, json=FAKE_RESPONSE, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    adapter = LemonadeTranscriptionAdapter("http://localhost:13305/api/v1")
    await adapter.transcribe(audio_path, language="es")

    assert captured["data"]["language"] == "es"
