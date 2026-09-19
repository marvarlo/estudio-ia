"""Tests de contrato del adaptador ElevenLabs -- igual filosofia que los
tests del skill original (stubear la llamada HTTP y afirmar la URL/payload
exactos ya verificados), pero con httpx en vez de urllib."""
import json

import httpx
import pytest

from app.adapters.outbound.tts.elevenlabs_tts import ElevenLabsTTSAdapter
from app.application.ports.tts import TTSRequest


@pytest.fixture()
def captured_request(monkeypatch):
    captured: dict = {}

    async def fake_post(self, url, json=None, headers=None):  # noqa: A002 - firma espeja httpx.AsyncClient.post
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = json
        return httpx.Response(200, content=b"fake-mp3-bytes", request=httpx.Request("GET", "https://test.local"))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    return captured


async def test_synthesize_posts_exact_verified_payload(captured_request):
    adapter = ElevenLabsTTSAdapter(api_key="test-key")

    result = await adapter.synthesize(TTSRequest(text="Hola mundo", voice_id="voice-123"))

    assert captured_request["url"] == "https://api.elevenlabs.io/v1/text-to-speech/voice-123"
    assert captured_request["headers"]["xi-api-key"] == "test-key"
    assert captured_request["headers"]["Accept"] == "audio/mpeg"
    assert captured_request["body"] == {"text": "Hola mundo", "model_id": "eleven_multilingual_v2"}
    assert result.audio_bytes == b"fake-mp3-bytes"
    assert result.provider == "elevenlabs"


async def test_synthesize_uses_requested_model_override(captured_request):
    adapter = ElevenLabsTTSAdapter(api_key="test-key")

    await adapter.synthesize(TTSRequest(text="hola", voice_id="v1", model="eleven_v3"))

    assert captured_request["body"]["model_id"] == "eleven_v3"


async def test_synthesize_without_api_key_raises():
    adapter = ElevenLabsTTSAdapter(api_key=None)

    with pytest.raises(RuntimeError, match="ELEVENLABS_API_KEY"):
        await adapter.synthesize(TTSRequest(text="x", voice_id="v1"))
