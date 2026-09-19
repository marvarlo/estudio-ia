"""Tests de contrato de los adaptadores de video -- afirman la forma exacta
de payload/endpoints portada de los scripts verificados del skill original
(wan_video.py, google_video.py) y el flujo de creacion+poll+descarga, sin
pegarle a ninguna API real. Gemini Omni queda con un test minimo: su propio
script origen ya lo marca como no confirmado contra la API real."""
from __future__ import annotations

import base64
import json

import httpx
import pytest

from app.adapters.outbound.video import omni_video, veo_video, wan_video
from app.application.ports.video_generation import VideoGenerationRequest


@pytest.fixture()
def image_file(tmp_path):
    path = tmp_path / "frame.png"
    path.write_bytes(b"fake-png-bytes")
    return path


@pytest.fixture()
def audio_file(tmp_path):
    path = tmp_path / "driving.mp3"
    path.write_bytes(b"fake-mp3-bytes")
    return path


async def test_wan_creates_task_polls_and_downloads(monkeypatch, image_file, audio_file):
    monkeypatch.setattr(wan_video, "POLL_INTERVAL_SECONDS", 0)
    calls = {"status_polls": 0}

    async def fake_post(self, url, json=None, headers=None):
        assert url == wan_video.CREATE_URL
        assert headers["Authorization"] == "Bearer test-ali-key"
        assert headers["X-DashScope-Async"] == "enable"
        assert json["model"] == "wan2.7-i2v"
        assert json["input"]["media"][0]["type"] == "first_frame"
        assert json["input"]["media"][1]["type"] == "driving_audio"
        assert json["parameters"]["consistency_mode"] == "strict"
        return httpx.Response(200, json={"output": {"task_id": "task-1"}}, request=httpx.Request("GET", "https://test.local"))

    async def fake_get(self, url, headers=None, params=None):
        if url == wan_video.STATUS_URL_TEMPLATE.format(task_id="task-1"):
            calls["status_polls"] += 1
            if calls["status_polls"] == 1:
                return httpx.Response(200, json={"output": {"task_status": "RUNNING"}}, request=httpx.Request("GET", "https://test.local"))
            return httpx.Response(200, json={"output": {"task_status": "SUCCEEDED", "video_url": "https://example.com/video.mp4"}}, request=httpx.Request("GET", "https://test.local"))
        if url == "https://example.com/video.mp4":
            return httpx.Response(200, content=b"fake-mp4-bytes", request=httpx.Request("GET", "https://test.local"))
        raise AssertionError(f"URL inesperada: {url}")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    adapter = wan_video.WanVideoAdapter(api_key="test-ali-key")
    result = await adapter.generate(
        VideoGenerationRequest(prompt="test", image_path=image_file, driving_audio_path=audio_file, duration_seconds=6.0)
    )

    assert result.video_bytes == b"fake-mp4-bytes"
    assert result.provider == "wan"
    assert calls["status_polls"] == 2  # una vez RUNNING, una vez SUCCEEDED


async def test_wan_raises_on_task_failure(monkeypatch, image_file, audio_file):
    monkeypatch.setattr(wan_video, "POLL_INTERVAL_SECONDS", 0)

    async def fake_post(self, url, json=None, headers=None):
        return httpx.Response(200, json={"output": {"task_id": "task-1"}}, request=httpx.Request("GET", "https://test.local"))

    async def fake_get(self, url, headers=None, params=None):
        return httpx.Response(200, json={"output": {"task_status": "FAILED", "message": "contenido rechazado"}}, request=httpx.Request("GET", "https://test.local"))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    adapter = wan_video.WanVideoAdapter(api_key="test-ali-key")
    with pytest.raises(RuntimeError, match="contenido rechazado"):
        await adapter.generate(VideoGenerationRequest(prompt="x", image_path=image_file, driving_audio_path=audio_file))


async def test_wan_requires_image_and_audio(image_file):
    adapter = wan_video.WanVideoAdapter(api_key="test-ali-key")
    with pytest.raises(ValueError, match="first_frame|image_path"):
        await adapter.generate(VideoGenerationRequest(prompt="x", image_path=image_file, driving_audio_path=None))


async def test_wan_without_api_key_raises(image_file, audio_file):
    adapter = wan_video.WanVideoAdapter(api_key=None)
    with pytest.raises(RuntimeError, match="ALI_API_KEY"):
        await adapter.generate(VideoGenerationRequest(prompt="x", image_path=image_file, driving_audio_path=audio_file))


async def test_veo_generates_synchronously_when_no_operation_name(monkeypatch, image_file):
    async def fake_post(self, url, params=None, json=None):
        assert "generateContent" in url
        assert json["generationConfig"]["videoConfig"]["durationSeconds"] == 8
        return httpx.Response(200, json={"video": {"bytesBase64Encoded": base64.b64encode(b"fake-mp4").decode()}}, request=httpx.Request("GET", "https://test.local"))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    adapter = veo_video.VeoVideoAdapter(api_key="test-google-key")
    result = await adapter.generate(VideoGenerationRequest(prompt="x", image_path=image_file, duration_seconds=20))

    assert result.video_bytes == b"fake-mp4"
    assert result.provider == "veo"


async def test_veo_without_image_path_raises():
    adapter = veo_video.VeoVideoAdapter(api_key="test-google-key")
    with pytest.raises(ValueError, match="image_path"):
        await adapter.generate(VideoGenerationRequest(prompt="x", image_path=None))


async def test_omni_posts_to_interactions_endpoint_with_image_and_text(monkeypatch, image_file):
    captured = {}

    async def fake_post(self, url, params=None, json=None):
        captured["url"] = url
        captured["body"] = json
        video_content = {"steps": [{"type": "model_output", "content": [{"type": "video", "data": base64.b64encode(b"fake-omni-mp4").decode()}]}]}
        return httpx.Response(200, json=video_content, request=httpx.Request("GET", "https://test.local"))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    adapter = omni_video.GeminiOmniVideoAdapter(api_key="test-google-key")
    result = await adapter.generate(VideoGenerationRequest(prompt="una escena", image_path=image_file, width=1280, height=720))

    assert captured["url"] == omni_video.OMNI_ENDPOINT
    assert captured["body"]["model"] == omni_video.OMNI_MODEL
    assert captured["body"]["input"][1] == {"type": "text", "text": "una escena"}
    assert result.video_bytes == b"fake-omni-mp4"
