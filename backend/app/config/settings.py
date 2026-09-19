"""Configuracion de la app. Lee variables de entorno directamente (sin
pydantic-settings, para no sumar una dependencia mas en la fase 0) via
EnvSecretStore -- ver adapters/outbound/secrets/env_secret_store.py."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.adapters.outbound.secrets.env_secret_store import EnvSecretStore

_BACKEND_ROOT = Path(__file__).resolve().parents[2]  # .../estudio-ia/backend
_REPO_ROOT = _BACKEND_ROOT.parent  # .../estudio-ia


@dataclass(frozen=True)
class Settings:
    workspace_dir: Path
    db_path: Path
    stories_root: Path
    lemonade_base_url: str
    gemini_api_key: str | None
    elevenlabs_api_key: str | None
    ali_api_key: str | None
    google_api_key: str | None

    @staticmethod
    def load() -> "Settings":
        secrets = EnvSecretStore()
        workspace = Path(secrets.get("ESTUDIO_IA_WORKSPACE") or (_REPO_ROOT / "workspace"))
        workspace.mkdir(parents=True, exist_ok=True)
        db_path = Path(secrets.get("ESTUDIO_IA_DB") or (workspace / "estudio-ia.db"))
        # Los proyectos NUEVOS (CreateStoryProjectUseCase) se escriben aca --
        # por defecto, la carpeta hermana `historias/` donde ya viven las
        # historias producidas con el skill original, para que un mismo
        # canal use una sola convencion de carpetas sin importar si el
        # proyecto se creo desde la web o se importo.
        stories_root = Path(secrets.get("ESTUDIO_IA_STORIES_ROOT") or (_REPO_ROOT.parent / "historias"))
        stories_root.mkdir(parents=True, exist_ok=True)
        return Settings(
            workspace_dir=workspace,
            db_path=db_path,
            stories_root=stories_root,
            lemonade_base_url=secrets.get("LEMONADE_BASE_URL") or "http://localhost:13305/api/v1",
            gemini_api_key=secrets.get("GEMINI_API_KEY"),
            elevenlabs_api_key=secrets.get("ELEVENLABS_API_KEY"),
            ali_api_key=secrets.get("ALI_API_KEY"),
            google_api_key=secrets.get("GOOGLE_API_KEY"),
        )
