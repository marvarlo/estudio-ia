import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export const FPS = 30;
export const CIERRE_SECONDS = 4;
export const CIERRE_FRAMES = CIERRE_SECONDS * FPS;

// Cartel final del video de TEMPORADA COMPLETA (build_season.py) -- no
// confundir con el "Fin" chico en la esquina del ultimo capitulo individual
// (Outro.tsx): ese cierra ESE episodio, este cierra el corte completo.
export const Cierre: React.FC = () => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "black",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          opacity,
          color: "white",
          fontFamily: "sans-serif",
          fontSize: 80,
          fontWeight: 700,
          letterSpacing: 6,
        }}
      >
        FIN
      </div>
    </AbsoluteFill>
  );
};
