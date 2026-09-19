// Estilo compartido de marca (intro, separadores de temporada, etc). El
// nombre real del canal es "ImaginArIA" -- un juego de palabras entre
// "Imaginaria" e "IA" -- y el tagline "Historias FantástIcAs" repite el
// mismo guino resaltando mayusculas incrustadas a mitad de palabra. Esta
// funcion es generica (no asume el texto exacto) para que siga funcionando
// si el nombre del canal cambia mas adelante: cualquier mayuscula que NO
// esté al inicio de una palabra se resalta con el color de acento.
export const ACCENT_COLOR = "#ff6b6b";

export const highlightEmbeddedCaps = (
  text: string,
  accentColor: string = ACCENT_COLOR,
) => {
  const words = text.split(" ");
  return words.map((word, wi) => (
    <span key={wi}>
      {word.split("").map((ch, ci) => {
        const isEmbeddedCap = ci > 0 && ch !== ch.toLowerCase() && ch === ch.toUpperCase();
        return (
          <span key={ci} style={isEmbeddedCap ? { color: accentColor } : undefined}>
            {ch}
          </span>
        );
      })}
      {wi < words.length - 1 ? " " : ""}
    </span>
  ));
};
