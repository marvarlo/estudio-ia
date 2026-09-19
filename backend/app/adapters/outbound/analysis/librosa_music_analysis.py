"""Analisis de estructura musical via librosa (BPM + beats reales) --
dependencia liviana (numpy/scipy/numba, sin PyTorch) a diferencia de Demucs,
asi que a diferencia de la separacion de fuentes esto SI se pudo instalar y
verificar en vivo en esta maquina (ver README, fase 5).

Deteccion de tonalidad y secciones (verso/coro) quedan fuera de alcance a
proposito -- el videoclip animado de esta fase solo necesita beats reales
para "cortar en el beat" (ver GenerateMusicVideoShotsUseCase), no analisis
armonico completo."""
from __future__ import annotations

from pathlib import Path

import librosa

from app.application.ports.music_analysis import MusicAnalysisResult


class LibrosaMusicAnalysisAdapter:
    async def analyze(self, audio_path: Path) -> MusicAnalysisResult:
        try:
            y, sr = librosa.load(str(audio_path), sr=None, mono=True)
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
            bpm = float(tempo[0]) if hasattr(tempo, "__len__") else float(tempo)
        except Exception:  # noqa: BLE001 - el analisis de beat es un plus, no un requisito duro
            return MusicAnalysisResult(bpm=None, key=None, sections=[], beats=[])

        return MusicAnalysisResult(bpm=bpm, key=None, sections=[], beats=beat_times)
