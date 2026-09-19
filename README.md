# Estudio IA

Estudio de producción audiovisual asistido por IA: historias cortas en
formato motion comic narrado, videos musicales animados, lyrics videos y
karaoke, con un wizard común de 4 pasos (Contenido → Cast → Storyboard →
Edición/Render) y un panel de proveedores de IA configurable.

Este repositorio es la migración del skill `historias-fantasia` (y de
`video-clip-creator`) a una aplicación web, siguiendo arquitectura
hexagonal. El plan completo, con las decisiones de arquitectura y la hoja de
ruta por fases, vive en el doc **"Estudio IA — Arquitectura y plan de
migración"**.

## Estado: Fase 0 (cimientos)

Lo que ya funciona:

- Backend hexagonal (FastAPI + SQLite) con dominio puro, puertos
  (`Protocol`) para cada capacidad de IA, y un `ProviderRegistry` con
  adaptadores reales contra **Lemonade Server** (texto, imagen, TTS —
  local) y validación de credenciales para **Gemini**/**ElevenLabs**.
- Panel de proveedores con prueba de humo real (`POST
  /api/providers/{id}/test`).
- Importador de historias ya producidas con el skill `historias-fantasia`
  (`historia_config.json`, `canon.md`, `personajes.json`, `escenarios.json`,
  `voces.json`, `capitulo-N/produccion.md` + sus assets) — sin copiar
  archivos, idempotente.
- Frontend (React + TypeScript + Tailwind) con lista de proyectos, detalle
  (cast, escenarios, voces) y visor de capítulos/shots con imagen y audio
  reales.

Lo que falta (ver la hoja de ruta del doc de arquitectura): escritura
asistida por LLM (canon, prosa, hoja de producción), generación real de
imagen/audio/video por shot con jobs y progreso, el sidecar de Remotion, y
todo el pipeline de música (demux, transcripción, sincronización, karaoke).

## Estructura

```
estudio-ia/
  backend/     FastAPI + SQLite, arquitectura hexagonal (ver backend/app/)
  frontend/    React + TypeScript + Vite + Tailwind
  render/      placeholder — sidecar Remotion (fase 3)
  packages/    placeholder — contratos compartidos (timeline.json, tipos)
  workspace/   datos del usuario (DB local, gitignored)
```

Ver `backend/app/` para el detalle de la arquitectura hexagonal:
`domain/` (entidades puras), `application/ports/` (interfaces de cada
capacidad de IA), `application/use_cases/` (casos de uso), `adapters/`
(API REST, SQLite, adaptadores de proveedores).

## Cómo correrlo

### Backend

Requiere Python 3.12+ y [`uv`](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Variables de entorno opcionales (todas tienen default razonable):

| Variable | Default | Para qué |
|---|---|---|
| `LEMONADE_BASE_URL` | `http://localhost:13305/api/v1` | Servidor local de modelos |
| `GEMINI_API_KEY` | — | Habilita el proveedor Gemini |
| `ELEVENLABS_API_KEY` | — | Habilita el proveedor ElevenLabs |
| `ESTUDIO_IA_WORKSPACE` | `./workspace` | Dónde vive la base de datos local |

Tests:

```bash
cd backend
uv run pytest
```

### Frontend

Requiere Node 20+.

```bash
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173`. Espera el backend corriendo en el puerto
8000 (CORS ya configurado para `localhost:5173`).

### Importar una historia ya producida

Desde la pantalla de Proyectos, pegar la ruta absoluta a la carpeta de una
historia ya producida con el skill `historias-fantasia` (por ejemplo
`C:\Users\Marco\proyectos\historias\la-bruja-del-espejo`) y presionar
"Importar carpeta". No copia ningún archivo — lee `produccion.md` y los
assets ya generados directamente desde ahí.
