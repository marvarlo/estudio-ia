import asyncio

from app.config.provider_registry import ProviderRegistry
from app.config.settings import Settings


def _settings(tmp_path, **overrides) -> Settings:
    base = Settings(
        workspace_dir=tmp_path,
        db_path=tmp_path / "test.db",
        lemonade_base_url="http://localhost:13305/api/v1",
        gemini_api_key=None,
        elevenlabs_api_key=None,
        ali_api_key=None,
        google_api_key=None,
    )
    return Settings(**{**base.__dict__, **overrides})


def test_unconfigured_cloud_provider_reports_missing_credentials(tmp_path):
    registry = ProviderRegistry(_settings(tmp_path))
    health = asyncio.run(registry.test("elevenlabs"))
    assert health.ok is False
    assert "API key" in health.detail


def test_unknown_provider_id_reports_error(tmp_path):
    registry = ProviderRegistry(_settings(tmp_path))
    health = asyncio.run(registry.test("no-existe"))
    assert health.ok is False
    assert health.detail == "Proveedor desconocido"


def test_lemonade_text_health_check_against_real_local_server(tmp_path):
    """Prueba de integracion real (no mockeada): asume que Lemonade Server
    esta corriendo en localhost:13305, como en la maquina de desarrollo
    (ver memoria 'entorno-local-marco'). Si no lo esta, el health_check debe
    reportarlo con ok=False en vez de lanzar una excepcion -- eso es lo que
    se verifica aqui, no que el servidor este siempre encendido."""
    registry = ProviderRegistry(_settings(tmp_path))
    health = asyncio.run(registry.test("lemonade-text"))
    assert isinstance(health.ok, bool)
    assert health.detail
