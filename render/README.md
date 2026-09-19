# render/

Sidecar Remotion de Estudio IA (fase 3). Renderiza el video final de un
capitulo a partir del `timeline.json` que arma el backend
(`backend/app/application/use_cases/render_chapter.py`) -- ya no lee
`scenes.json` de disco como el prototipo original en `video-prototype/`
(fuera de este monorepo).

## Como se invoca

El backend (`RemotionRenderAdapter`,
`backend/app/adapters/outbound/render/remotion_render_adapter.py`) NO usa
`npx remotion render`: en Windows, invocar `npx` desde un subproceso Python
falla por un AutoRun de `cmd.exe` roto ("DOSKEY no se reconoce"), nada que
ver con Remotion. El adaptador va directo al entry point real de la CLI con
`node.exe`:

```bash
node node_modules/@remotion/cli/remotion-cli.js render Capitulo salida.mp4 --props=props.json
```

con la variable de entorno `RENDER_PUBLIC_DIR` apuntando a
`capitulo-N/assets/` -- las rutas de imagen/audio/video del timeline vienen
relativas a esa carpeta (via `staticFile()`, igual que `build_scenes.py` del
skill original las generaba relativas a esa misma carpeta). `props.json`
tiene la forma `{"timeline": {...}}` (ver `src/Capitulo.tsx`, tipo
`Timeline`). Cada invocacion es un proceso nuevo, asi que la variable de
entorno cambia libremente de un capitulo a otro sin estado compartido -- no
hay bundle ni servidor persistente que mantener.

## Composiciones

- **Capitulo**: la principal (fase 3). `calculateMetadata` resuelve
  duracion/resolucion en base al `timeline` recibido (numero de escenas
  variable por capitulo, a diferencia del prototipo original que asumia un
  unico `scenes.json` fijo).
- **LyricsVideo** / **Karaoke** / **MusicVideo** (fases 4-5, `src/Lyrics.tsx`):
  comparten componente, solo cambia el prop `mode`. A diferencia de
  "Capitulo", NO hay audio por escena -- una unica pista maestra
  (`timeline.audio`) suena de punta a punta, y cada escena se posiciona en
  su ventana de tiempo REAL (`Sequence` con `from` absoluto en vez de
  encadenarse con pausas de 1s, que desincronizarian el video del audio).
  Karaoke ademas resalta cada palabra segun `timeline.lyrics.lines[].words[]`
  comparando el tiempo absoluto de la cancion contra el `start`/`end` de
  cada palabra. MusicVideo oculta los subtitulos por completo (el
  videoclip animado no muestra letra en pantalla) -- sus shots vienen en
  ventanas de ~8s cortadas en el beat con personaje/escenario consistentes,
  ver `GenerateMusicVideoShotsUseCase`.
- **Separador** / **Cierre**: piezas sueltas para el corte de TEMPORADA
  COMPLETA (fase 5) -- se renderizan aparte y se concatenan con
  `RenderPort.concat()` (ffmpeg, sin recodificar) junto a los mp4 de cada
  capitulo.

`src/camera.ts` tiene el parseo de "Movimiento Camara" (Ken Burns) --
compartido por Capitulo y Lyrics, no duplicado.

## Desarrollo local

```bash
npm install   # primera vez -- descarga tambien el chrome-headless-shell de Remotion
npm run dev   # abre Remotion Studio para inspeccionar las composiciones sueltas
```

`remotion.config.ts` solo exige `RENDER_PUBLIC_DIR` cuando hay assets reales
que servir (renderizar "Capitulo" con escenas) -- Remotion Studio arranca
igual sin la variable para inspeccionar Separador/Cierre.

## Verificado en vivo (fase 3)

Render real de un capitulo completo (52 escenas) de una historia ya
producida (`la-bruja-del-espejo`, capitulo 1), con imagenes y audio reales
generados en la fase 2 -- intro con el nombre del proyecto, Ken Burns segun
la columna "Movimiento Camara", subtitulos quemados con los audio tags
limpiados, audio real no silencioso, resolucion y duracion tomadas del
timeline via `calculateMetadata`. Video final servido de vuelta al frontend
via `/api/media` y reproducible en el navegador.

## Verificado en vivo (fase 4)

Pipeline completo real via la API (no solo props.json de prueba): una
cancion real ("Noches en B-Wing") transcrita con Lemonade, editada en
lineas, convertida en shots, con fondos generados por Lemonade, renderizada
como Karaoke -- resaltado palabra a palabra sincronizado con los timestamps
reales de la transcripcion, pista maestra sonando de punta a punta, corte a
negro correcto en los huecos entre lineas (sin escena activa). Encontrado y
corregido en el camino: el generador de imagen local (Flux-2-Klein-4B)
tomaba la letra citada entre comillas en el prompt como texto literal a
dibujar en la imagen -- se solucion o quitando las comillas y reforzando la
regla anti-texto (ver `GenerateShotsFromLyricsUseCase`).

## Verificado en vivo (fase 5)

Pipeline completo real del videoclip animado: elenco generado por LLM a
partir de la letra transcrita, beats reales detectados con librosa (140.6
BPM en un test con musica real), 4 shots en ventanas de ~8s cortadas en el
beat, fondos generados por Lemonade con personaje/escenario CONSISTENTES en
las 4 escenas (mismo protagonista, mismo club B-Wing con luces rojas/azules)
gracias a reutilizar `GenerateShotImageUseCase` sin tocarla, renderizado como
MusicVideo sin subtitulos, audio real de punta a punta.

**Bug real encontrado y corregido ANTES de renderizar** (revision de codigo,
no en producción): `BuildMusicTimelineUseCase` reconstruia el tiempo
absoluto de cada shot buscando la linea de letra en la misma posicion de
indice (`lines[i]`) -- funcionaba por casualidad con LyricsVideo/Karaoke
(una linea = un shot, 1:1), pero con las ventanas de beat del videoclip
animado (mas shots que lineas) generaba tiempos superpuestos e incorrectos.
Se agrego `Shot.start_seg` (tiempo absoluto propio de cada shot) como fuente
de verdad para todos los productos de musica.

**Limitacion real observada, mitigada pero no eliminada**: el generador de
imagen local alucina texto garabateado sobre ropa descripta como "band
t-shirt"/"printed logo" (mismo tipo de problema que las comillas de la fase
4, causa distinta) -- se agrego una regla al prompt de casting pidiendo
describir la ropa por corte/color/material en vez de por lo que dice o
representa, sin una segunda verificacion en vivo por tiempo.
