import json
from pathlib import Path

from fastapi.testclient import TestClient


def _make_client(tmp_path: Path, monkeypatch) -> TestClient:
    # Workspace/DB propios por test -- nunca tocar el workspace real del
    # usuario (donde viven sus proyectos importados de verdad).
    monkeypatch.setenv("ESTUDIO_IA_WORKSPACE", str(tmp_path))
    from app.main import app  # import diferido: debe leer el env var recien seteado

    return TestClient(app)


def test_health_endpoint(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch)
    with client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_providers_are_listed_with_lemonade_configured_by_default(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch)
    with client:
        response = client.get("/api/providers")
    assert response.status_code == 200
    providers = {p["id"]: p for p in response.json()}
    assert providers["lemonade-text"]["configured"] is True
    assert providers["elevenlabs"]["configured"] is False


def test_import_then_list_projects_then_chapter_shots(tmp_path, monkeypatch):
    story_root = tmp_path / "historias" / "mi-historia-api-test"
    story_root.mkdir(parents=True)
    (story_root / "historia_config.json").write_text(
        json.dumps({"historia": "mi-historia-api-test", "estilo_visual": "anime", "tono": "NORMAL"}),
        encoding="utf-8",
    )
    (story_root / "canon.md").write_text("# CANON — API Test\n", encoding="utf-8")
    chapter_dir = story_root / "capitulo-1"
    chapter_dir.mkdir()
    (chapter_dir / "produccion.md").write_text(
        "# Capítulo 1 — Uno\n\n"
        "| # | Tipo | Texto |\n|---|---|---|\n"
        "| 1 | Narracion | Hola mundo |\n",
        encoding="utf-8",
    )

    client = _make_client(tmp_path, monkeypatch)
    with client:
        import_response = client.post("/api/projects/import", json={"path": str(story_root)})
        assert import_response.status_code == 200
        summary = import_response.json()
        assert summary["chapters_imported"] == 1
        assert summary["shots_imported"] == 1

        list_response = client.get("/api/projects")
        assert list_response.status_code == 200
        projects = list_response.json()
        assert len(projects) == 1
        assert projects[0]["slug"] == "mi-historia-api-test"

        detail_response = client.get(f"/api/projects/{summary['project_id']}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        chapter_id = detail["chapters"][0]["id"]

        shots_response = client.get(f"/api/chapters/{chapter_id}/shots")
        assert shots_response.status_code == 200
        shots_payload = shots_response.json()
        assert shots_payload["shots"][0]["texto"] == "Hola mundo"


def test_get_unknown_project_returns_404(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch)
    with client:
        response = client.get("/api/projects/no-existe")
    assert response.status_code == 404
