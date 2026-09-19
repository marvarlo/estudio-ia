import {
  AbsoluteFill,
  Series,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Sequence,
} from "remotion";
import { Audio, Video } from "@remotion/media";
import { cameraStyle, parseCameraMove } from "./camera";
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
