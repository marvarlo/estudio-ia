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

## Estado: Fase 2 (Storyboard)

Lo que ya funciona:

- **Fase 0 — Cimientos:** backend hexagonal (FastAPI + SQLite), puertos
  (`Protocol`) para cada capacidad de IA, `ProviderRegistry` con adaptadores
  reales contra **Lemonade Server** (texto, imagen, TTS — local), panel de
  proveedores con prueba de humo real, e importador de historias ya
  producidas con el skill `historias-fantasia` (sin copiar archivos,
  idempotente).
- **Fase 1 — Contenido y cast:** generación de canon y cast (personajes +
  escenarios) por LLM con JSON estructurado, casting automático de voces
  desde un pool a nivel canal, generación de fichas de referencia (imagen),
  y una tabla de producción totalmente editable en la web (crear/editar/
  eliminar/reordenar shots) con linter en vivo y exportación de vuelta a
  `produccion.md`.
- **Fase 2 — Storyboard:** generación real de imagen/audio/video **por
  shot**, encolada como `Job` asíncrono con progreso consultable
  (`GET /api/jobs/{id}`) en vez de bloquear la request; cada generación crea
  un `Asset` nuevo sin borrar los anteriores (historial de versiones
  navegable y seleccionable desde la UI); generación por lote a nivel
  capítulo para imagen y audio (salta lo que ya tiene una versión
  seleccionada, salvo `force`); adaptadores para **Gemini** (imagen con
  referencias multimodales para consistencia de personaje/escenario),
  **ElevenLabs** (TTS), y video (**WAN 2.7** lip-sync, **Google Veo 3.1**,
  **Gemini Omni** — experimental, sin confirmar contra la API real).

Sin credenciales de proveedores cloud en esta máquina, Gemini/ElevenLabs/
WAN/Veo/Omni están implementados y cubiertos por tests de contrato
(payloads verificados contra los scripts originales, sin pegarle a la API
real), pero solo los proveedores Lemonade están probados end-to-end con
llamadas reales en este entorno.

Lo que falta (ver la hoja de ruta del doc de arquitectura): escritura de
prosa completa de capítulos por LLM y derivación automática de la hoja de
producción desde esa prosa, el sidecar de Remotion (fase 3), y todo el
pipeline de música (demux, transcripción, sincronización, karaoke — fase 4).

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
| `GEMINI_API_KEY` | — | Habilita Gemini (texto, imagen) |
| `ELEVENLABS_API_KEY` | — | Habilita ElevenLabs (TTS) |
| `ALI_API_KEY` | — | Habilita WAN 2.7 (DashScope, video con lip-sync) |
| `GOOGLE_API_KEY` | — | Habilita Veo 3.1 y Gemini Omni (video) |
| `ESTUDIO_IA_WORKSPACE` | `./workspace` | Dónde vive la base de datos local |
| `ESTUDIO_IA_STORIES_ROOT` | `../historias` (carpeta hermana) | Dónde se crean los proyectos nuevos |

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
