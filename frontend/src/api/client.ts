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
  num_episodios: number | null
  duracion_objetivo_min: number | null
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
  slug: string
  nombre: string
  rol: string
  tokens_visuales: Record<string, string>
  reference_image_path: string | null
}

export type Location = {
  id: string
  slug: string
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

export type SeasonEpisode = { numero: number; resumen: string; cliffhanger: string }

export type Canon = {
  logline: string
  premisa: string
  reglas_sistema: string
  glosario: string
  temporada: SeasonEpisode[]
  raw_markdown: string
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

export type ShotWrite = {
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
}

export type ChapterShots = {
  chapter: Chapter
  shots: Shot[]
}

export type LintWarning = {
  severity: "warning" | "info"
  message: string
  shot_id: string | null
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

export type VoicePoolVoice = {
  id: string
  proveedor: string
  voice_id_externo: string
  nombre_interno: string
  modelo_tts: string
  atributos: Record<string, string>
  veces_usada: number
  ultima_historia: string | null
}

export type Asset = {
  id: string
  kind: string
  path: string
  width: number | null
  height: number | null
  provider: string
  model: string
}

export type JobStatus = "pending" | "running" | "done" | "failed" | "cancelled"

export type Job = {
  id: string
  kind: string
  provider: string
  shot_id: string | null
  status: JobStatus
  progress: number
  result: Record<string, string> | null
  error: string | null
  cost_estimate: number | null
  cost_actual: number | null
}

export type BatchGenerateResult = {
  jobs: Job[]
  skipped: number
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
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  // Proyectos
  listProjects: () => request<Project[]>("/api/projects"),
  createProject: (data: { name: string; estilo_visual?: string; tono?: string; plataformas?: string[] }) =>
    request<Project>("/api/projects", { method: "POST", body: JSON.stringify(data) }),
  getProject: (projectId: string) => request<ProjectDetail>(`/api/projects/${projectId}`),
  importProject: (path: string) =>
    request<ImportSummary>("/api/projects/import", { method: "POST", body: JSON.stringify({ path }) }),

  // Canon
  getCanon: (projectId: string) => request<Canon>(`/api/projects/${projectId}/canon`),
  generateCanon: (
    projectId: string,
    data: {
      estilo_narrativo: string
      tono: string
      plataformas: string[]
      estilo_visual: string
      num_episodios: number
      duracion_objetivo_min: number
      semilla: string
      provider_id: string
    },
  ) => request<Canon>(`/api/projects/${projectId}/canon:generate`, { method: "POST", body: JSON.stringify(data) }),

  // Cast
  generateCast: (projectId: string, data: { num_personajes: number; num_escenarios: number; notas: string; provider_id: string }) =>
    request<{ characters: Character[]; locations: Location[] }>(`/api/projects/${projectId}/cast:generate`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  assignVoices: (projectId: string) => request<Voice[]>(`/api/projects/${projectId}/voices:assign`, { method: "POST" }),

  // Fichas de referencia
  generateCharacterSheet: (characterId: string, providerId = "lemonade-image") =>
    request<Asset>(`/api/characters/${characterId}/sheet:generate`, {
      method: "POST",
      body: JSON.stringify({ provider_id: providerId }),
    }),
  generateLocationSheet: (locationId: string, providerId = "lemonade-image") =>
    request<Asset>(`/api/locations/${locationId}/sheet:generate`, {
      method: "POST",
      body: JSON.stringify({ provider_id: providerId }),
    }),

  // Pool de voces
  listVoicePool: () => request<VoicePoolVoice[]>("/api/voice-pool"),
  addVoiceToPool: (data: { proveedor: string; voice_id_externo: string; nombre_interno?: string; modelo_tts?: string }) =>
    request<VoicePoolVoice>("/api/voice-pool", { method: "POST", body: JSON.stringify(data) }),

  // Capitulos / shots
  createChapter: (projectId: string, titulo: string, numero?: number) =>
    request<Chapter>("/api/chapters", { method: "POST", body: JSON.stringify({ project_id: projectId, titulo, numero }) }),
  getChapterShots: (chapterId: string) => request<ChapterShots>(`/api/chapters/${chapterId}/shots`),
  createShot: (chapterId: string, data: ShotWrite) =>
    request<Shot>(`/api/chapters/${chapterId}/shots`, { method: "POST", body: JSON.stringify(data) }),
  updateShot: (shotId: string, data: ShotWrite) =>
    request<Shot>(`/api/shots/${shotId}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteShot: (shotId: string) => request<void>(`/api/shots/${shotId}`, { method: "DELETE" }),
  reorderShots: (chapterId: string, orderedShotIds: string[]) =>
    request<Shot[]>(`/api/chapters/${chapterId}/shots:reorder`, {
      method: "POST",
      body: JSON.stringify({ ordered_shot_ids: orderedShotIds }),
    }),
  lintChapter: (chapterId: string) => request<LintWarning[]>(`/api/chapters/${chapterId}/lint`),
  exportChapter: (chapterId: string) => request<{ path: string }>(`/api/chapters/${chapterId}/export`, { method: "POST" }),

  // Generacion por shot (fase 2): imagen / audio / video, jobs, versionado
  generateShotImage: (shotId: string, providerId: string, select = true) =>
    request<Job>(`/api/shots/${shotId}/image:generate`, {
      method: "POST",
      body: JSON.stringify({ provider_id: providerId, select }),
    }),
  generateShotAudio: (shotId: string, providerId: string, select = true) =>
    request<Job>(`/api/shots/${shotId}/audio:generate`, {
      method: "POST",
      body: JSON.stringify({ provider_id: providerId, select }),
    }),
  generateShotVideo: (shotId: string, providerId: string, select = true) =>
    request<Job>(`/api/shots/${shotId}/video:generate`, {
      method: "POST",
      body: JSON.stringify({ provider_id: providerId, select }),
    }),
  generateChapterImages: (chapterId: string, providerId: string, force = false) =>
    request<BatchGenerateResult>(`/api/chapters/${chapterId}/images:generate`, {
      method: "POST",
      body: JSON.stringify({ provider_id: providerId, force }),
    }),
  generateChapterAudio: (chapterId: string, providerId: string, force = false) =>
    request<BatchGenerateResult>(`/api/chapters/${chapterId}/audio:generate`, {
      method: "POST",
      body: JSON.stringify({ provider_id: providerId, force }),
    }),
  getJob: (jobId: string) => request<Job>(`/api/jobs/${jobId}`),
  listShotAssets: (shotId: string) => request<Asset[]>(`/api/shots/${shotId}/assets`),
  selectShotAsset: (shotId: string, assetId: string) =>
    request<Shot>(`/api/shots/${shotId}/assets:select`, { method: "POST", body: JSON.stringify({ asset_id: assetId }) }),

  // Proveedores
  listProviders: () => request<Provider[]>("/api/providers"),
  testProvider: (providerId: string) => request<ProviderHealth>(`/api/providers/${providerId}/test`, { method: "POST" }),
}

/** Poll a un job hasta que llegue a un estado terminal (done/failed/cancelled). */
export async function pollJob(jobId: string, { intervalMs = 1500, timeoutMs = 10 * 60 * 1000 } = {}): Promise<Job> {
  const deadline = Date.now() + timeoutMs
  while (true) {
    const job = await api.getJob(jobId)
    if (job.status === "done" || job.status === "failed" || job.status === "cancelled") return job
    if (Date.now() > deadline) throw new Error(`Job ${jobId} no termino a tiempo`)
    await new Promise((resolve) => setTimeout(resolve, intervalMs))
  }
}

// Los assets viven fuera de este proyecto (en la carpeta de la historia) --
// se sirven via /api/media?path=... en vez de un mount estatico fijo, ver
// adapters/inbound/api/routers/media.py.
export function mediaUrl(path: string | null): string | null {
  if (!path) return null
  return `${API_BASE}/api/media?path=${encodeURIComponent(path)}`
}

export const emptyShotWrite = (): ShotWrite => ({
  tipo: "Narracion",
  personaje_ids: [],
  escenario_id: null,
  sub_escenario: "",
  momento_dia: "",
  texto: "",
  prompt_imagen: "",
  prompt_video: "",
  movimiento_camara: "",
  duracion_estimada_seg: null,
  sfx_musica: "",
})

export const shotToWrite = (shot: Shot): ShotWrite => ({
  tipo: shot.tipo,
  personaje_ids: shot.personaje_ids,
  escenario_id: shot.escenario_id,
  sub_escenario: shot.sub_escenario,
  momento_dia: shot.momento_dia,
  texto: shot.texto,
  prompt_imagen: shot.prompt_imagen,
  prompt_video: shot.prompt_video,
  movimiento_camara: shot.movimiento_camara,
  duracion_estimada_seg: shot.duracion_estimada_seg,
  sfx_musica: shot.sfx_musica,
})
