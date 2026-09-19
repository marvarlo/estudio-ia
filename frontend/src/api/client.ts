// Cliente HTTP minimo contra el backend FastAPI. Sin generacion de tipos
// desde OpenAPI todavia (llega en una fase posterior, ver seccion 4 del doc
// de arquitectura, "contratos compartidos") -- estos tipos se escriben a
// mano y deben mantenerse en sync con app/adapters/inbound/api/schemas.py.

export const API_BASE = "http://localhost:8000"

export type Project = {
  id: string
  slug: string
  name: string
  kind: string
  estilo_visual: string
  tono: string
  plataformas: string[]
  formatos: string[]
  root_path: string
}

export type Chapter = {
  id: string
  numero: number
  titulo: string
  estado: "borrador" | "hoja_derivada" | "assets" | "renderizado"
  tiene_prosa: boolean
}

export type Character = {
  id: string
  nombre: string
  rol: string
  reference_image_path: string | null
}

export type Location = {
  id: string
  nombre: string
  descripcion_fija: string
  reference_image_path: string | null
}

export type Voice = {
  id: string
  personaje_id: string | null
  proveedor: string
  voice_id_externo: string
  notas_direccion: string
}

export type ProjectDetail = {
  project: Project
  logline: string
  chapters: Chapter[]
  characters: Character[]
  locations: Location[]
  voices: Voice[]
}

export type Shot = {
  id: string
  orden: number
  tipo: string
  personaje_ids: string[]
  escenario_id: string | null
  sub_escenario: string
  momento_dia: string
  texto: string
  prompt_imagen: string
  prompt_video: string
  movimiento_camara: string
  duracion_estimada_seg: number | null
  sfx_musica: string
  image_asset_path: string | null
  audio_asset_path: string | null
  video_asset_path: string | null
}

export type ChapterShots = {
  chapter: Chapter
  shots: Shot[]
}

export type ImportSummary = {
  project_id: string
  slug: string
  name: string
  chapters_imported: number
  shots_imported: number
  characters_imported: number
  locations_imported: number
  voices_imported: number
  assets_found: number
  warnings: string[]
}

export type Provider = {
  id: string
  name: string
  kind: "local" | "cloud"
  capabilities: string[]
  configured: boolean
}

export type ProviderHealth = {
  ok: boolean
  detail: string
  latency_ms: number | null
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(typeof body.detail === "string" ? body.detail : response.statusText)
  }
  return response.json() as Promise<T>
}

export const api = {
  listProjects: () => request<Project[]>("/api/projects"),
  getProject: (projectId: string) => request<ProjectDetail>(`/api/projects/${projectId}`),
  importProject: (path: string) =>
    request<ImportSummary>("/api/projects/import", {
      method: "POST",
      body: JSON.stringify({ path }),
    }),
  getChapterShots: (chapterId: string) => request<ChapterShots>(`/api/chapters/${chapterId}/shots`),
  listProviders: () => request<Provider[]>("/api/providers"),
  testProvider: (providerId: string) =>
    request<ProviderHealth>(`/api/providers/${providerId}/test`, { method: "POST" }),
}

// Los assets viven fuera de este proyecto (en la carpeta de la historia) --
// se sirven via /api/media?path=... en vez de un mount estatico fijo, ver
// adapters/inbound/api/routers/media.py.
export function mediaUrl(path: string | null): string | null {
  if (!path) return null
  return `${API_BASE}/api/media?path=${encodeURIComponent(path)}`
}
