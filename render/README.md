# render/

Placeholder para la fase 3 (Render). Hoy el proyecto Remotion vive en un
repo hermano, `video-prototype/` (fuera de este monorepo), tal como lo dejo
el skill `historias-fantasia`.

La fase 3 lo convierte en un sidecar Node invocado por el backend via
`RenderPort` (ver `backend/app/application/ports/render.py` y la seccion 7
del doc de arquitectura "Estudio IA — Arquitectura y plan de migracion"):

- Copiar/migrar las composiciones de `video-prototype/src/*.tsx` aca.
- Reemplazar `scenes.json` leido de disco por `timeline.json` recibido como
  `inputProps` de `@remotion/renderer`.
- Envolver `renderMedia` en un pequeno servidor Express/Fastify que el
  backend Python invoca por HTTP local.
- Agregar `MusicVideo`, `LyricsVideo`, `Karaoke`, `Short` como composiciones
  nuevas (fase 4-5).

No crear nada aca todavia si no es esa fase -- evita que este monorepo
cargue un `node_modules` de Remotion sin usar.
