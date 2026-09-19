"""Contract tests del adaptador: verifican la forma del comando invocado
(sin lanzar Node de verdad -- eso ya se probo en vivo end-to-end, ver
README.md fase 3) y el manejo de errores cuando el subproceso falla."""
from __future__ import annotations

import json

import pytest

from app.adapters.outbound.render.remotion_render_adapter import RemotionRenderAdapter
from app.application.ports.media_probe import MediaInfo
from app.application.ports.render import RenderRequest


class FakeMediaProbe:
    def probe(self, path):
        return MediaInfo(duration_seconds=12.3)


class FakeProcess:
    def __init__(self, returncode: int, stdout: bytes = b"", stderr: bytes = b"") -> None:
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    async def communicate(self):
        return self._stdout, self._stderr


def _make_render_project(tmp_path):
    project_dir = tmp_path / "render"
    cli = project_dir / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
    cli.parent.mkdir(parents=True)
    cli.write_text("// fake cli")
    return project_dir


async def test_render_invokes_node_cli_with_props_file_and_public_dir(tmp_path, monkeypatch):
    project_dir = _make_render_project(tmp_path)
    adapter = RemotionRenderAdapter(project_dir, FakeMediaProbe())
    monkeypatch.setattr("shutil.which", lambda name: "C:/node.exe" if name == "node" else None)

    captured = {}

    async def fake_exec(*cmd, cwd, env, stdout, stderr):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["env"] = env
        return FakeProcess(returncode=0)

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_exec)

    output_path = tmp_path / "out" / "capitulo1.mp4"
    public_dir = tmp_path / "capitulo-1" / "assets"
    request = RenderRequest(
        composition_id="Capitulo",
        timeline={"meta": {"canal": "x"}, "escenas": []},
        output_path=output_path,
        public_dir=public_dir,
    )

    result = await adapter.render(request)

    assert result.output_path == output_path
    assert result.duration_seconds == 12.3
    cmd = captured["cmd"]
    assert cmd[0] == "C:/node.exe"
    assert str(project_dir / "node_modules" / "@remotion" / "cli" / "remotion-cli.js") in cmd
    assert "render" in cmd
    assert "Capitulo" in cmd
    assert str(output_path) in cmd
    props_arg = next(a for a in cmd if a.startswith("--props="))
    props_path = props_arg.removeprefix("--props=")
    # El archivo temporal de props se borra despues de invocar -- verificamos
    # el contenido via el mock antes de que el finally lo elimine no es
    # posible aca, asi que solo confirmamos que se referencio un .json real.
    assert props_path.endswith(".json")
    assert captured["env"]["RENDER_PUBLIC_DIR"] == str(public_dir)
    assert captured["cwd"] == str(project_dir)


async def test_render_raises_with_stderr_on_nonzero_exit(tmp_path, monkeypatch):
    project_dir = _make_render_project(tmp_path)
    adapter = RemotionRenderAdapter(project_dir, FakeMediaProbe())
    monkeypatch.setattr("shutil.which", lambda name: "C:/node.exe")

    async def fake_exec(*cmd, cwd, env, stdout, stderr):
        return FakeProcess(returncode=1, stderr=b"algo salio mal en Remotion")

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_exec)

    request = RenderRequest(
        composition_id="Capitulo",
        timeline={"meta": {}, "escenas": []},
        output_path=tmp_path / "out.mp4",
        public_dir=tmp_path,
    )

    with pytest.raises(RuntimeError, match="algo salio mal"):
        await adapter.render(request)


async def test_render_raises_when_node_missing(tmp_path, monkeypatch):
    project_dir = _make_render_project(tmp_path)
    adapter = RemotionRenderAdapter(project_dir, FakeMediaProbe())
    monkeypatch.setattr("shutil.which", lambda name: None)

    request = RenderRequest(
        composition_id="Capitulo", timeline={}, output_path=tmp_path / "out.mp4", public_dir=tmp_path,
    )

    with pytest.raises(RuntimeError, match="node.exe"):
        await adapter.render(request)


async def test_props_file_contains_the_timeline(tmp_path, monkeypatch):
    project_dir = _make_render_project(tmp_path)
    adapter = RemotionRenderAdapter(project_dir, FakeMediaProbe())
    monkeypatch.setattr("shutil.which", lambda name: "C:/node.exe")

    written_props = {}

    async def fake_exec(*cmd, cwd, env, stdout, stderr):
        props_arg = next(a for a in cmd if a.startswith("--props="))
        props_path = props_arg.removeprefix("--props=")
        written_props["data"] = json.loads(open(props_path, encoding="utf-8").read())
        return FakeProcess(returncode=0)

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_exec)

    timeline = {"meta": {"canal": "Test"}, "escenas": [{"numero": "01"}]}
    request = RenderRequest(
        composition_id="Capitulo", timeline=timeline, output_path=tmp_path / "out.mp4", public_dir=tmp_path,
    )
    await adapter.render(request)

    assert written_props["data"] == {"timeline": timeline}


async def test_separador_and_cierre_props_are_not_wrapped_in_timeline(tmp_path, monkeypatch):
    """Separador/Cierre (corte de temporada) tienen props planos propios
    ({numeroCapitulo, tituloCapitulo} o {} vacio) -- no son parte del
    contrato timeline.json, asi que NO deben ir envueltos como las demas
    composiciones."""
    project_dir = _make_render_project(tmp_path)
    adapter = RemotionRenderAdapter(project_dir, FakeMediaProbe())
    monkeypatch.setattr("shutil.which", lambda name: "C:/node.exe")

    written_props = {}

    async def fake_exec(*cmd, cwd, env, stdout, stderr):
        props_arg = next(a for a in cmd if a.startswith("--props="))
        props_path = props_arg.removeprefix("--props=")
        written_props["data"] = json.loads(open(props_path, encoding="utf-8").read())
        return FakeProcess(returncode=0)

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_exec)

    request = RenderRequest(
        composition_id="Separador",
        timeline={"numeroCapitulo": 2, "tituloCapitulo": "La Caida"},
        output_path=tmp_path / "separador.mp4",
        public_dir=tmp_path,
    )
    await adapter.render(request)

    assert written_props["data"] == {"numeroCapitulo": 2, "tituloCapitulo": "La Caida"}
