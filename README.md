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

## Estado: Fase 4 + huecos cerrados (prosa completa y corte de temporada)

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
- **Fase 3 — Render:** sidecar Remotion en `render/` (ver `render/README.md`)
  invocado por el backend via `RenderPort`/`RemotionRenderAdapter`, que arma
  el `timeline.json` de un capítulo a partir de los shots ya generados
  (imagen+audio, o video con lip-sync si lo hay) midiendo la duración REAL de
  cada uno; render encolado como `Job` (puede tardar varios minutos, no es
  una generación puntual); cada render crea un `Asset` de video nuevo sin
  borrar los anteriores, igual que la regla de versionado de la fase 2; el
  video final queda reproducible desde la página del capítulo.
- **Fase 4 — Música (lyrics video / karaoke):** subir un MP3/WAV crea un
  proyecto de música (reutiliza `Project`/`Chapter`/`Shot` del dominio de
  historias — "en música el mismo concepto cubre una ventana de la
  canción", ya documentado desde la fase 0 — así hereda sin tocarla toda la
  infraestructura de generación de imagen, versionado y jobs de la fase 2);
  transcripción real con **Lemonade** (`Whisper-Large-v3-Turbo`, endpoint
  OpenAI-compatible `/audio/transcriptions`, con timestamps por palabra y
  flag de "sospechosa" igual que `transcribe.py` del skill
  `video-clip-creator`); editor simple de líneas de letra (texto/tiempos,
  no un editor de forma de onda todavía); una línea de letra = un shot,
  con generación de fondo reutilizando `GenerateShotImageUseCase` sin
  cambios; render de **LyricsVideo** y **Karaoke** (resaltado palabra a
  palabra) como composiciones nuevas de Remotion, con la pista maestra
  sonando de punta a punta y cada escena posicionada en su ventana de
  tiempo REAL (no secuencial con pausas, como sí hace "Capitulo").

Sin credenciales de proveedores cloud en esta máquina, Gemini/ElevenLabs/
WAN/Veo/Omni están implementados y cubiertos por tests de contrato
(payloads verificados contra los scripts originales, sin pegarle a la API
real), igual que Demucs (separación de fuentes: sin GPU/PyTorch instalados
aquí). Lemonade (texto/imagen/TTS/transcripción) y el render con Remotion
son 100% locales y están probados end-to-end con ejecuciones reales,
incluyendo un pipeline completo real (canción → transcripción → shots →
fondos → video de Karaoke) en este entorno.

- **Prosa completa por LLM + derivación de hoja de producción** (hueco que
  había quedado fuera de la fase 1): "Escribir con IA" genera la prosa
  completa de un capítulo (párrafos reales, no una lista de líneas) a
  partir del resumen/cliffhanger de ese capítulo en el esqueleto de
  temporada del canon; el usuario puede revisarla/corregirla en un editor
  simple antes de "Derivar hoja de producción", que la convierte en shots
  (tipo, personajes, escenario, prompt de imagen con tokens `[id]`,
  movimiento de cámara, duración estimada) reutilizando el mismo LLM.
  Simplificación deliberada: el modelo elige entre personajes/escenarios ya
  existentes en vez de poder crear escenarios nuevos sobre la marcha.
- **Corte de temporada completa**: un botón en la página del proyecto
  concatena todos los capítulos ya renderizados individualmente (fase 3)
  con separadores "Capítulo N: Título" entre cada uno y un cartel "FIN" al
  final -- usa `RenderPort.concat()` (ffmpeg, sin recodificar), que ya
  estaba implementado y testeado desde la fase 3 pero sin caso de uso que
  lo invocara.

Lo que falta (ver la hoja de ruta del doc de arquitectura): separación de
fuentes verificada en vivo (Demucs/instrumental para Karaoke — hoy Karaoke
usa la pista que se suba tal cual), detección de estructura musical (BPM/
secciones), un editor de sincronización con forma de onda, y el videoclip
musical animado con cast/escenarios (necesita generación narrativa por LLM
como canon/cast, no solo transcripción).

## Estructura

```
estudio-ia/
  backend/     FastAPI + SQLite, arquitectura hexagonal (ver backend/app/)
  frontend/    React + TypeScript + Vite + Tailwind
  render/      sidecar Remotion (fase 3) -- ver render/README.md
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
| `ESTUDIO_IA_RENDER_DIR` | `../render` (carpeta hermana) | Proyecto Remotion del sidecar de render (fase 3) |

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

### Renderizar un capítulo

Requiere `node`/`npm` (para el sidecar Remotion) y `ffmpeg`/`ffprobe` en el
PATH. Primera vez:

```bash
cd render
npm install   # tambien descarga el chrome-headless-shell de Remotion
```

Con el backend corriendo, el botón "Renderizar capítulo" de la página de un
capítulo (o `POST /api/chapters/{id}/render:generate`) arma el
`timeline.json` a partir de las imágenes/audio ya seleccionados por shot y
lo renderiza con Remotion -- ver `render/README.md` para el detalle de cómo
se invoca la CLI.

### Crear un videoclip de letra / karaoke

Desde "+ Nuevo videoclip de letra", subí un MP3/WAV y elegí el tipo
(Lyrics video o Karaoke). El pipeline es: transcribir (Lemonade, real) →
revisar/editar las líneas → generar shots desde la letra → generar un fondo
por shot (Lemonade, reutiliza la misma generación de imagen de historias) →
renderizar. No hace falta ninguna variable de entorno nueva -- usa el mismo
`LEMONADE_BASE_URL`.

### Importar una historia ya producida

Desde la pantalla de Proyectos, pegar la ruta absoluta a la carpeta de una
historia ya producida con el skill `historias-fantasia` (por ejemplo
`C:\Users\Marco\proyectos\historias\la-bruja-del-espejo`) y presionar
"Importar carpeta". No copia ningún archivo — lee `produccion.md` y los
assets ya generados directamente desde ahí.
