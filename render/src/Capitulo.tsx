import {
  AbsoluteFill,
  Series,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
  Sequence,
} from "remotion";
import { Audio, Video } from "@remotion/media";
import { Intro, INTRO_FRAMES, INTRO_CROSSFADE_FRAMES } from "./Intro";
import { Outro, OUTRO_FRAMES } from "./Outro";

export const FPS = 30;

// Descanso entre escenas: sin esto, la siguiente linea de narracion/dialogo
// arranca en el instante exacto en que termina el audio anterior, lo que se
// siente "corrido" -- no le da al espectador un respiro para leer/procesar
// la imagen. La imagen se sostiene 1s en silencio antes del corte.
const PAUSE_SECONDS = 1;

export type Scene = {
  numero: string;
  tipo: string;
  texto: string;
  subtitulo: string;
  movimiento_camara: string;
  imagen: string | null;
  audio: string | null;
  video: string | null;
  durationInSeconds: number;
};

export type TimelineMeta = {
  canal: string;
  tagline: string;
  numeroCapitulo: number;
  tituloCapitulo: string | null;
  outroLabel: string;
  width: number;
  height: number;
};

// Contrato compartido con el backend Python (BuildChapterTimelineUseCase,
// app/application/use_cases/render_chapter.py) -- las rutas de imagen/audio/
// video vienen relativas a RENDER_PUBLIC_DIR (ver remotion.config.ts), igual
// que build_scenes.py del skill original las generaba relativas a
// `capitulo-N/assets/`.
export type Timeline = {
  meta: TimelineMeta;
  escenas: Scene[];
};

export type CapituloProps = { timeline: Timeline };

const sceneDurationInFrames = (s: Scene) =>
  Math.ceil((s.durationInSeconds + PAUSE_SECONDS) * FPS);

export const getTotalDurationInFrames = (timeline: Timeline) => {
  const totalScenes = timeline.escenas.reduce((sum, s) => sum + sceneDurationInFrames(s), 0);
  // La primera escena arranca INTRO_CROSSFADE_FRAMES antes de que la intro
  // termine (se superponen), asi que esos frames no se suman dos veces.
  return INTRO_FRAMES - INTRO_CROSSFADE_FRAMES + totalScenes + OUTRO_FRAMES;
};

// La columna "Movimiento Camara" de produccion.md YA trae directivas reales
// en espanol (zoom in/out, pan izquierda/derecha, estatico, con lento/rapido/
// muy rapido como intensidad) -- ver references/formato_produccion.md. No
// hace falta una columna nueva para Remotion, solo interpretar esta bien.
type CameraMove = {
  kind: "static" | "zoom_in" | "zoom_out" | "pan_left" | "pan_right";
  amplitude: number;
};

const parseCameraMove = (raw: string): CameraMove => {
  const m = raw.toLowerCase();
  if (!m || m.includes("estatico") || m.includes("está")) {
    return { kind: "static", amplitude: 0 };
  }
  const amplitude = m.includes("muy rapido")
    ? 0.16
    : m.includes("rapido")
      ? 0.11
      : m.includes("lento")
        ? 0.045
        : 0.07;

  if (m.includes("zoom out")) return { kind: "zoom_out", amplitude };
  if (m.includes("zoom")) return { kind: "zoom_in", amplitude };
  if (m.includes("pan izquierda")) return { kind: "pan_left", amplitude };
  if (m.includes("pan derecha")) return { kind: "pan_right", amplitude };
  // "pan rapido" sin lado -- direccion no especificada en produccion.md,
  // se asume derecha (mismo criterio que usaria un editor al no saber cual).
  if (m.includes("pan")) return { kind: "pan_right", amplitude };

  // Ninguna directiva reconocida: Ken Burns leve en vez de imagen muerta.
  return { kind: "zoom_in", amplitude: 0.045 };
};

const cameraStyle = (
  move: CameraMove,
  frame: number,
  durationInFrames: number,
): React.CSSProperties => {
  const easing = Easing.bezier(0.16, 1, 0.3, 1);
  const t = (from: number, to: number) =>
    interpolate(frame, [0, durationInFrames], [from, to], {
      easing,
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

  switch (move.kind) {
    case "static":
      return { transform: "scale(1)" };
    case "zoom_in":
      return { transform: `scale(${t(1, 1 + move.amplitude)})` };
    case "zoom_out":
      return { transform: `scale(${t(1 + move.amplitude, 1)})` };
    case "pan_left": {
      // Headroom extra (amplitude) para poder desplazar sin mostrar bordes.
      const x = t(move.amplitude * 50, -move.amplitude * 50);
      return { transform: `scale(${1 + move.amplitude}) translateX(${x}%)` };
    }
    case "pan_right": {
      const x = t(-move.amplitude * 50, move.amplitude * 50);
      return { transform: `scale(${1 + move.amplitude}) translateX(${x}%)` };
    }
  }
};

const SceneView: React.FC<{ scene: Scene; fadeInFrames?: number }> = ({ scene, fadeInFrames = 8 }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const move = parseCameraMove(scene.movimiento_camara);

  // Fade in/out corto entre escenas para que los cortes no sean secos. La
  // primera escena del capitulo recibe un fadeInFrames mas largo (ver
  // Capitulo.tsx) para que coincida con la ventana de crossfade de la Intro.
  const fade = interpolate(
    frame,
    [0, fadeInFrames, durationInFrames - 8, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <AbsoluteFill style={{ opacity: fade }}>
        {scene.video ? (
          // Clip ya animado (Veo/WAN/etc, via "Prompt Video" en produccion.md)
          // -- trae su propio movimiento y su propio audio (narracion o
          // dialogo, con lip-sync si el modelo lo soporta). Reemplaza a
          // imagen+audio+camara sintetica por completo, no se combinan.
          <Video
            src={staticFile(scene.video)}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        ) : (
          <img
            src={staticFile(scene.imagen as string)}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              ...cameraStyle(move, frame, durationInFrames),
            }}
          />
        )}
        {scene.subtitulo ? (
          <AbsoluteFill
            style={{
              justifyContent: "flex-end",
              alignItems: "center",
              paddingBottom: 80,
            }}
          >
            <div
              style={{
                maxWidth: "80%",
                fontFamily: "sans-serif",
                fontSize: 34,
                fontWeight: 600,
                color: "white",
                textAlign: "center",
                textShadow: "0 2px 10px rgba(0,0,0,0.9)",
                background: "rgba(0,0,0,0.35)",
                padding: "14px 28px",
                borderRadius: 12,
              }}
            >
              {scene.subtitulo}
            </div>
          </AbsoluteFill>
        ) : null}
      </AbsoluteFill>
      {scene.video ? null : (
        <Sequence layout="none">
          <Audio src={staticFile(scene.audio as string)} />
        </Sequence>
      )}
    </AbsoluteFill>
  );
};

export const Capitulo: React.FC<CapituloProps> = ({ timeline }) => {
  const { meta, escenas } = timeline;
  return (
    <Series>
      <Series.Sequence durationInFrames={INTRO_FRAMES} name="intro">
        <Intro
          canal={meta.canal}
          tagline={meta.tagline}
          numeroCapitulo={meta.numeroCapitulo}
          tituloCapitulo={meta.tituloCapitulo ?? undefined}
        />
      </Series.Sequence>
      {escenas.map((scene, i) => (
        <Series.Sequence
          key={scene.numero}
          durationInFrames={sceneDurationInFrames(scene)}
          // Solo la primera escena se superpone con la cola de la Intro
          // (crossfade); el resto encadena normalmente, sin offset.
          offset={i === 0 ? -INTRO_CROSSFADE_FRAMES : 0}
          name={`escena-${scene.numero}`}
        >
          <SceneView scene={scene} fadeInFrames={i === 0 ? INTRO_CROSSFADE_FRAMES : 8} />
        </Series.Sequence>
      ))}
      <Series.Sequence durationInFrames={OUTRO_FRAMES} name="outro">
        <Outro label={meta.outroLabel} />
      </Series.Sequence>
    </Series>
  );
};
