import { Easing, interpolate } from "remotion";

// La columna "Movimiento Camara" de produccion.md (o, en musica, el mismo
// campo en el shot generado por linea de letra) YA trae directivas reales en
// espanol (zoom in/out, pan izquierda/derecha, estatico, con lento/rapido/
// muy rapido como intensidad) -- ver references/formato_produccion.md. No
// hace falta una columna nueva para Remotion, solo interpretar esta bien.
// Extraido de Capitulo.tsx (fase 3) para reutilizar en Lyrics.tsx (fase 4)
// sin duplicar la logica.
export type CameraMove = {
  kind: "static" | "zoom_in" | "zoom_out" | "pan_left" | "pan_right";
  amplitude: number;
};

export const parseCameraMove = (raw: string): CameraMove => {
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
  // "pan rapido" sin lado -- direccion no especificada, se asume derecha
  // (mismo criterio que usaria un editor al no saber cual).
  if (m.includes("pan")) return { kind: "pan_right", amplitude };

  // Ninguna directiva reconocida: Ken Burns leve en vez de imagen muerta.
  return { kind: "zoom_in", amplitude: 0.045 };
};

export const cameraStyle = (
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
      const x = t(move.amplitude * 50, -move.amplitude * 50);
      return { transform: `scale(${1 + move.amplitude}) translateX(${x}%)` };
    }
    case "pan_right": {
      const x = t(-move.amplitude * 50, move.amplitude * 50);
      return { transform: `scale(${1 + move.amplitude}) translateX(${x}%)` };
    }
  }
};
