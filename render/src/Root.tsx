import "./index.css";
import { Composition } from "remotion";
import { Capitulo, FPS, getTotalDurationInFrames, Timeline } from "./Capitulo";
import { Separador, SEPARADOR_FRAMES } from "./Separador";
import { Cierre, CIERRE_FRAMES } from "./Cierre";

const EMPTY_TIMELINE: Timeline = {
  meta: {
    canal: "ImaginArIA",
    tagline: "Historias FantástIcAs",
    numeroCapitulo: 1,
    tituloCapitulo: null,
    outroLabel: "Continuará",
    width: 1920,
    height: 1080,
  },
  escenas: [],
};

// Composicion principal: recibe `timeline` como inputProps (--props= al
// invocar la CLI, ver RemotionRenderAdapter), ya NO lee scenes.json de disco
// -- eso era del prototipo original en video-prototype/, pensado para un
// unico proyecto renderizado a mano. `calculateMetadata` resuelve la
// duracion/resolucion reales en base al timeline recibido, porque cada
// capitulo tiene un numero de escenas y una relacion de aspecto distintos.
//
// Separador y Cierre son piezas sueltas para armar el video de TEMPORADA
// COMPLETA (fase 5): se renderizan aparte y se concatenan con ffmpeg junto a
// los mp4 de cada capitulo -- no forman parte de "Capitulo" porque ese sigue
// siendo el render de un episodio individual.
export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Capitulo"
        component={Capitulo}
        fps={FPS}
        width={EMPTY_TIMELINE.meta.width}
        height={EMPTY_TIMELINE.meta.height}
        durationInFrames={FPS}
        defaultProps={{ timeline: EMPTY_TIMELINE }}
        calculateMetadata={async ({ props }) => {
          const timeline = (props as { timeline: Timeline }).timeline;
          return {
            durationInFrames: Math.max(1, getTotalDurationInFrames(timeline)),
            width: timeline.meta.width || 1920,
            height: timeline.meta.height || 1080,
          };
        }}
      />
      <Composition
        id="Separador"
        component={Separador}
        fps={FPS}
        width={1920}
        height={1080}
        durationInFrames={SEPARADOR_FRAMES}
        defaultProps={{ numeroCapitulo: 1, tituloCapitulo: "" }}
      />
      <Composition
        id="Cierre"
        component={Cierre}
        fps={FPS}
        width={1920}
        height={1080}
        durationInFrames={CIERRE_FRAMES}
      />
    </>
  );
};
