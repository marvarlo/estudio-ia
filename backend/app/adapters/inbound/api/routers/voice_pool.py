from __future__ import annotations

from fastapi import APIRouter, Depends

from app.adapters.inbound.api.deps import get_repository
from app.adapters.inbound.api.schemas import VoicePoolAddRequest, VoicePoolVoiceOut
from app.application.use_cases.voice_pool import AddVoiceToPoolUseCase, ListVoicePoolUseCase

router = APIRouter(prefix="/api/voice-pool", tags=["voice-pool"])


@router.get("", response_model=list[VoicePoolVoiceOut])
def list_voice_pool(repository=Depends(get_repository)) -> list[VoicePoolVoiceOut]:
    voices = ListVoicePoolUseCase(repository).execute()
    return [VoicePoolVoiceOut.from_domain(v) for v in voices]


@router.post("", response_model=VoicePoolVoiceOut)
def add_voice_to_pool(payload: VoicePoolAddRequest, repository=Depends(get_repository)) -> VoicePoolVoiceOut:
    voice = AddVoiceToPoolUseCase(repository).execute(
        proveedor=payload.proveedor,
        voice_id_externo=payload.voice_id_externo,
        nombre_interno=payload.nombre_interno,
        modelo_tts=payload.modelo_tts,
        atributos=payload.atributos,
    )
    return VoicePoolVoiceOut.from_domain(voice)
