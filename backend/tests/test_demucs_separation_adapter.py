"""Contrato del adaptador Demucs -- NO verificado en vivo en esta maquina
(sin GPU/PyTorch instalado, ver README fase 4); estos tests fijan la forma
del comando y el manejo de errores via subprocess mockeado."""
from __future__ import annotations

import pytest

from app.adapters.outbound.separation.demucs_separation import DemucsSeparationAdapter


class FakeProcess:
    def __init__(self, returncode: int, stdout: bytes = b"", stderr: bytes = b"") -> None:
        self.returncode = returncode
        self._stdout, self._stderr = stdout, stderr

    async def communicate(self):
        return self._stdout, self._stderr


async def test_separate_invokes_demucs_and_finds_stems(tmp_path, monkeypatch):
    audio_path = tmp_path / "song.mp3"
    audio_path.write_bytes(b"fake")
    adapter = DemucsSeparationAdapter(output_root=tmp_path / "out", demucs_command="demucs")
    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")

    calls = []

    async def fake_exec(*cmd, stdout, stderr):
        calls.append(cmd)
        if cmd[0].endswith("demucs"):
            # Simula que demucs ya escribio los stems antes de que
            # comuniquemos con el proceso (mismo orden que el subproceso real).
            stems_dir = tmp_path / "out" / "song" / "htdemucs_6s" / "song"
            stems_dir.mkdir(parents=True, exist_ok=True)
            for name in ("vocals", "drums", "bass"):
                (stems_dir / f"{name}.wav").write_bytes(b"wav")
            return FakeProcess(returncode=0)
        return FakeProcess(returncode=0)

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_exec)

    result = await adapter.separate(audio_path)

    assert "vocals" in result.stems
    assert "drums" in result.stems
    assert "bass" in result.stems
    demucs_cmd = calls[0]
    assert demucs_cmd[0] == "/usr/bin/demucs"
    assert "-n" in demucs_cmd and "htdemucs_6s" in demucs_cmd
    assert str(audio_path) in demucs_cmd


async def test_separate_raises_on_nonzero_exit(tmp_path, monkeypatch):
    audio_path = tmp_path / "song.mp3"
    audio_path.write_bytes(b"fake")
    adapter = DemucsSeparationAdapter(output_root=tmp_path / "out")
    monkeypatch.setattr("shutil.which", lambda name: name)

    async def fake_exec(*cmd, stdout, stderr):
        return FakeProcess(returncode=1, stderr=b"CUDA no disponible")

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_exec)

    with pytest.raises(RuntimeError, match="CUDA no disponible"):
        await adapter.separate(audio_path)
