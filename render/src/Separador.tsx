import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";

export const FPS = 30;
export const SEPARADOR_SECONDS = 3;
export const SEPARADOR_FRAMES = SEPARADOR_SECONDS * FPS;

export type SeparadorProps = {
  numeroCapitulo: number;
  tituloCapitulo?: string;
};

// Tarjeta entre capitulos cuando se arma el video de temporada completa
// (scripts/build_season.py) -- NO se usa en capitulos individuales, esos ya
// tienen su propia Intro. Un capitulo suelto no necesita anunciarse a si
// mismo dos veces.
export const Separador: React.FC<SeparadorProps> = ({ numeroCapitulo, tituloCapitulo }) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(
    frame,
    [0, 20, SEPARADOR_FRAMES - 20, SEPARADOR_FRAMES],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const scale = interpolate(frame, [0, 25], [0.94, 1], {
    easing: Easing.out(Easing.cubic),
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
      <div style={{ opacity, transform: `scale(${scale})`, textAlign: "center", fontFamily: "sans-serif" }}>
        <div
          style={{
            fontSize: 30,
            fontWeight: 600,
            color: "rgba(255,255,255,0.6)",
            letterSpacing: 3,
            textTransform: "uppercase",
          }}
        >
          Capítulo {numeroCapitulo}
        </div>
        {tituloCapitulo ? (
          <div style={{ fontSize: 48, fontWeight: 700, color: "white", marginTop: 8 }}>
            {tituloCapitulo}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
