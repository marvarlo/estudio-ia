/**
 * Note: When using the Node.JS APIs, the config file
 * doesn't apply. Instead, pass options directly to the APIs.
 *
 * All configuration options: https://remotion.dev/docs/config
 */

import path from "node:path";
import { Config } from "@remotion/cli/config";
import { enableTailwind } from "@remotion/tailwind-v4";

Config.setRspack(true);
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.overrideBundlerConfig(enableTailwind);

// RemotionRenderAdapter (backend/app/adapters/outbound/render/) invoca este
// proyecto como subproceso `node .../remotion-cli.js render Capitulo ...`
// con RENDER_PUBLIC_DIR apuntando a `capitulo-N/assets/` -- las rutas de
// imagen/audio/video del timeline vienen relativas a esa carpeta (via
// staticFile(), ver Capitulo.tsx). Cada render es un proceso nuevo, asi que
// esta variable puede cambiar libremente de un capitulo a otro sin estado
// compartido.
//
// Si falta (por ejemplo al correr `npm run dev` para inspeccionar las
// composiciones sueltas, Separador/Cierre, que no usan assets de ninguna
// historia), usar el directorio actual como default inofensivo en vez de
// tronar -- solo "Capitulo" con escenas reales necesita esto de verdad.
const renderPublicDir = process.env.RENDER_PUBLIC_DIR;
if (renderPublicDir) {
  Config.setPublicDir(path.resolve(renderPublicDir));
}
