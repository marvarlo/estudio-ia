"""Contrato del adaptador de imagen de Lemonade -- en particular, que el
mensaje de error final nunca quede vacio cuando todas las rutas fallan con
una excepcion sin mensaje propio (ej. httpx.ReadTimeout), un caso real
observado en vivo mas de una vez durante la verificacion de la fase 5."""
from __future__ import annotations

import httpx
import pytest

from app.adapters.outbound.image.lemonade_image import LemonadeImageAdapter
from app.application.ports.image_generation import ImageGenerationRequest


async def test_generate_raises_with_class_name_when_error_message_is_empty(monkeypatch):
    adapter = LemonadeImageAdapter("http://localhost:13305/api/v1")

    async def fake_post(self, url, json=None):
        raise httpx.ReadTimeout("")  # str() de esto es "" -- el caso real observado

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(RuntimeError, match="ReadTimeout"):
        await adapter.generate(ImageGenerationRequest(prompt="x", width=1280, height=720))


async def test_generate_raises_with_real_message_when_present(monkeypatch):
    adapter = LemonadeImageAdapter("http://localhost:13305/api/v1")

    async def fake_post(self, url, json=None):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(RuntimeError, match="connection refused"):
        await adapter.generate(ImageGenerationRequest(prompt="x", width=1280, height=720))
