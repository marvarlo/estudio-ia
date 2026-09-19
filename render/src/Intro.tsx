import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { highlightEmbeddedCaps } from "./Branding";

export const FPS = 30;
export const INTRO_SECONDS = 4;
export const INTRO_CROSSFADE_SECONDS = 1;
export const INTRO_FRAMES = INTRO_SECONDS * FPS;
export const INTRO_CROSSFADE_FRAMES = INTRO_CROSSFADE_SECONDS * FPS;

export type IntroProps = {
  canal: string;
  tagline: string;
  numeroCapitulo: number;
  tituloCapitulo?: string;
};

// Sin logo real todavia (placeholder de texto, ver README) -- la marca entra
// primero, el numero/titulo del capitulo despues. Los ultimos frames de este
// componente NO se desvanecen por si solos: la primera escena real se monta
// encima con un fade-in largo (ver Capitulo.tsx) y el cruce entre ambos es
// lo que produce el crossfade, no un fade-out propio de la intro.
export const Intro: React.FC<IntroProps> = ({
  canal,
  tagline,
  numeroCapitulo,
  tituloCapitulo,
}) => {
  const frame = useCurrentFrame();

  const brandOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const brandScale = interpolate(frame, [0, 20], [0.9, 1], {
    easing: Easing.out(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const chapterOpacity = interpolate(frame, [30, 55], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#0b0b12",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          opacity: brandOpacity,
          transform: `scale(${brandScale})`,
          textAlign: "center",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ fontSize: 92, fontWeight: 800, color: "white", letterSpacing: 1 }}>
          {highlightEmbeddedCaps(canal)}
        </div>
        <div
          style={{
            fontSize: 30,
            fontWeight: 500,
            color: "rgba(255,255,255,0.75)",
            marginTop: 10,
            letterSpacing: 2,
            textTransform: "uppercase",
          }}
        >
          {highlightEmbeddedCaps(tagline)}
        </div>
      </div>

      <div
        style={{
          opacity: chapterOpacity,
          textAlign: "center",
          fontFamily: "sans-serif",
          marginTop: 48,
        }}
      >
        <div
          style={{
            fontSize: 26,
            fontWeight: 600,
            color: "rgba(255,255,255,0.6)",
            letterSpacing: 3,
            textTransform: "uppercase",
          }}
        >
          Capítulo {numeroCapitulo}
        </div>
        {tituloCapitulo ? (
          <div style={{ fontSize: 40, fontWeight: 700, color: "white", marginTop: 6 }}>
            {tituloCapitulo}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
