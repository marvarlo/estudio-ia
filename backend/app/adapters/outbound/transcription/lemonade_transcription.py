"""Adaptador de transcripcion contra Lemonade Server (Whisper-Large-v3-Turbo,
recipe whispercpp) -- endpoint OpenAI-compatible `/audio/transcriptions`,
verificado en vivo contra un audio real de este proyecto: devuelve
`segments[].words[]` con inicio/fin/probabilidad por palabra, igual que
faster-whisper (`scripts/transcribe.py` del skill `video-clip-creator`), asi
que no hace falta instalar faster-whisper/PyTorch aparte -- Lemonade ya lo
sirve local."""
from __future__ import annotations

import time

import httpx

from app.application.ports.provider_health import ProviderHealth
from app.application.ports.transcription import TranscribedWord, TranscriptionResult

DEFAULT_MODEL = "Whisper-Large-v3-Turbo"

# Mismos umbrales que scripts/transcribe.py del skill video-clip-creator:
# Whisper alucina en cortes instrumentales/notas sostenidas -- una palabra de
# baja confianza o de duracion implausible se marca "suspect" en vez de
# tomarse como letra real sin revisar.
SUSPECT_PROBABILITY = 0.35
SUSPECT_DURATION_SECONDS = 5.0


class LemonadeTranscriptionAdapter:
    def __init__(self, base_url: str, model: str = DEFAULT_MODEL, timeout: float = 300.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    async def transcribe(self, audio_path, language: str | None = None) -> TranscriptionResult:
        data = {
            "model": self._model,
            "response_format": "verbose_json",
            "timestamp_granularities[]": "word",
        }
        if language:
            data["language"] = language

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            with open(audio_path, "rb") as fh:
                files = {"file": (audio_path.name, fh, "application/octet-stream")}
                response = await client.post(f"{self._base_url}/audio/transcriptions", data=data, files=files)
            response.raise_for_status()
            payload = response.json()

        words: list[TranscribedWord] = []
        for segment in payload.get("segments", []):
            for word in segment.get("words", []):
                start, end = float(word["start"]), float(word["end"])
                probability = float(word.get("probability", 1.0))
                suspect = probability < SUSPECT_PROBABILITY or (end - start) > SUSPECT_DURATION_SECONDS
                words.append(
                    TranscribedWord(
                        text=word["word"].strip(),
                        start=start,
                        end=end,
                        probability=probability,
                        suspect=suspect,
                    )
                )

        return TranscriptionResult(
            words=words,
            language=payload.get("language", language or ""),
            raw_text=payload.get("text", "").strip(),
        )

    async def health_check(self) -> ProviderHealth:
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/models")
                response.raise_for_status()
                data = response.json()
            model_ids = {m.get("id") for m in data.get("data", [])}
            latency_ms = (time.perf_counter() - start) * 1000
            if self._model in model_ids:
                return ProviderHealth(ok=True, detail=f"Modelo '{self._model}' descargado y listo", latency_ms=latency_ms)
            return ProviderHealth(ok=True, detail=f"Servidor accesible; '{self._model}' no listado", latency_ms=latency_ms)
        except Exception as exc:  # noqa: BLE001
            return ProviderHealth(ok=False, detail=f"No se pudo contactar Lemonade Server en {self._base_url}: {exc}")
