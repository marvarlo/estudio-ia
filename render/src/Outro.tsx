import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export const FPS = 30;
export const OUTRO_SECONDS = 3;
export const OUTRO_FRAMES = OUTRO_SECONDS * FPS;

export type OutroProps = {
  // "Continuará" en capitulos normales, "Fin" en el ultimo de la temporada
  // (a diferenciar del cartel "FIN" grande del corte de temporada completa,
  // ver Cierre.tsx -- este es el cierre discreto de UN capitulo individual).
  label: string;
};

// La ultima escena real ya se desvanece a negro por su cuenta (ver el fade
// de Scene en Capitulo.tsx) -- este componente arranca ya en negro y solo
// se encarga de traer el texto de cierre, sin otro fundido superpuesto.
export const Outro: React.FC<OutroProps> = ({ label }) => {
  const frame = useCurrentFrame();

  const textOpacity = interpolate(frame, [15, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "flex-end", padding: 64 }}>
        <div
          style={{
            opacity: textOpacity,
            color: "white",
            fontFamily: "sans-serif",
            fontSize: 38,
            fontWeight: 600,
            letterSpacing: 1,
          }}
        >
          {label}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
