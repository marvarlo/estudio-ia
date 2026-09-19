from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.adapters.inbound.api.deps import get_repository

router = APIRouter(prefix="/api/media", tags=["media"])


def _is_within(target: Path, root: Path) -> bool:
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False


@router.get("")
def get_media_file(path: str = Query(...), repository=Depends(get_repository)) -> FileResponse:
    """Sirve un archivo por ruta absoluta, validando que quede DENTRO de la
    carpeta raiz de algun proyecto ya importado. Evita que este endpoint se
    convierta en un servidor de archivos de todo el disco -- los binarios de
    un proyecto se quedan donde estan (seccion 10 del doc de arquitectura,
    'no se copian los 5 GB ya generados')."""
    target = Path(path).resolve()
    projects = repository.list_projects()
    if not any(_is_within(target, project.root_path.resolve()) for project in projects):
        raise HTTPException(status_code=403, detail="Ruta fuera de cualquier proyecto importado")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(target)
