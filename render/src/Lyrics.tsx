import { AbsoluteFill, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Audio } from "@remotion/media";
import { cameraStyle, parseCameraMove } from "./camera";

export const FPS = 30;
const ACCENT_COLOR = "#ffd166";

export type MusicScene = {
  numero: string;
  texto: string;
  subtitulo: string;
  movimiento_camara: string;
  imagen: string;
  start: number;
  end: number;
};

export type LyricWordTiming = { text: string; start: number; end: number };
export type LyricLineTiming = { text: string; start: number; end: number; words: LyricWordTiming[] };

export type MusicTimeline = {
  meta: { canal: string; width: number; height: number; durationInSeconds: number };
  audio: { path: string; volume: number };
  escenas: MusicScene[];
  lyrics: { lines: LyricLineTiming[] };
};

export type LyricsProps = { timeline: MusicTimeline; mode: "lyrics" | "karaoke" | "music" };

export const getTotalDurationInFrames = (timeline: MusicTimeline) =>
  Math.max(1, Math.round(timeline.meta.durationInSeconds * FPS));

// Karaoke: cada palabra cambia de color segun el tiempo ABSOLUTO de la
// cancion (no el frame relativo a la escena) comparado con su propio
// start/end -- exactamente los timestamps que devolvio la transcripcion
// (ver LemonadeTranscriptionAdapter), sin reinterpretar nada.
const KaraokeLine: React.FC<{ line: LyricLineTiming; absoluteTimeSeconds: number }> = ({ line, absoluteTimeSeconds }) => (
  <>
    {line.words.map((word, i) => {
      const sung = absoluteTimeSeconds >= word.end;
      const active = absoluteTimeSeconds >= word.start && absoluteTimeSeconds < word.end;
      const color = active ? ACCENT_COLOR : sung ? "white" : "rgba(255,255,255,0.45)";
      return (
        <span key={i} style={{ color, transition: "color 80ms linear" }}>
          {word.text}{" "}
        </span>
      );
    })}
  </>
);

const SceneView: React.FC<{ scene: MusicScene; line: LyricLineTiming | undefined; mode: "lyrics" | "karaoke" | "music" }> = ({
  scene,
  line,
  mode,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const move = parseCameraMove(scene.movimiento_camara);
  const absoluteTimeSeconds = scene.start + frame / FPS;

  const fade = interpolate(frame, [0, 8, durationInFrames - 8, durationInFrames], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <AbsoluteFill style={{ opacity: fade }}>
        <img
          src={staticFile(scene.imagen)}
          style={{ width: "100%", height: "100%", objectFit: "cover", ...cameraStyle(move, frame, durationInFrames) }}
        />
        {mode === "music" ? null : (
          <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 96 }}>
            <div
              style={{
                maxWidth: "85%",
                fontFamily: "sans-serif",
                fontSize: 40,
                fontWeight: 700,
                textAlign: "center",
                textShadow: "0 2px 12px rgba(0,0,0,0.9)",
                background: "rgba(0,0,0,0.4)",
                padding: "18px 32px",
                borderRadius: 14,
                color: "white",
              }}
            >
              {mode === "karaoke" && line ? <KaraokeLine line={line} absoluteTimeSeconds={absoluteTimeSeconds} /> : scene.subtitulo}
            </div>
          </AbsoluteFill>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// LyricsVideo, Karaoke y MusicVideo comparten esta composicion (solo
// cambia `mode`, fijo por Composition en Root.tsx -- "music" oculta los
// subtitulos por completo, ya que el videoclip animado no muestra letra en
// pantalla) -- las tres reciben el mismo timeline con
// UNA pista maestra de audio en vez de audio por escena (a diferencia de
// Capitulo.tsx), asi que cada escena se posiciona en su ventana de tiempo
// REAL (Sequence con `from` absoluto) en vez de encadenarse con pausas de
// 1s: insertar pausas aca desincronizaria el video del audio real.
export const Lyrics: React.FC<LyricsProps> = ({ timeline, mode }) => {
  const { audio, escenas, lyrics } = timeline;
  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {audio?.path ? <Audio src={staticFile(audio.path)} volume={audio.volume ?? 1} /> : null}
      {escenas.map((scene, i) => (
        <Sequence
          key={scene.numero}
          from={Math.round(scene.start * FPS)}
          durationInFrames={Math.max(1, Math.round((scene.end - scene.start) * FPS))}
          name={`linea-${scene.numero}`}
        >
          <SceneView scene={scene} line={lyrics.lines[i]} mode={mode} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
