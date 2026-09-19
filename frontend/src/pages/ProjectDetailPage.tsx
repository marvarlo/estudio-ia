import { useEffect, useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { api, mediaUrl, type ProjectDetail } from "../api/client"

const estadoLabel: Record<string, string> = {
  borrador: "Borrador",
  hoja_derivada: "Hoja derivada",
  assets: "Con assets",
  renderizado: "Renderizado",
}

const estadoColor: Record<string, string> = {
  borrador: "bg-zinc-700 text-zinc-200",
  hoja_derivada: "bg-blue-900 text-blue-200",
  assets: "bg-emerald-900 text-emerald-200",
  renderizado: "bg-violet-900 text-violet-200",
}

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [detail, setDetail] = useState<ProjectDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [sheetLoading, setSheetLoading] = useState<string | null>(null)

  function reload() {
    if (!projectId) return
    api
      .getProject(projectId)
      .then(setDetail)
      .catch((err) => setError(String(err.message ?? err)))
  }

  useEffect(reload, [projectId])

  async function handleNewChapter() {
    if (!projectId) return
    const titulo = window.prompt("Titulo del nuevo capitulo:", "Capítulo nuevo")
    if (!titulo) return
    try {
      const chapter = await api.createChapter(projectId, titulo)
      navigate(`/chapters/${chapter.id}`)
    } catch (err) {
      setError(String((err as Error).message ?? err))
    }
  }

  async function handleCharacterSheet(characterId: string) {
    setSheetLoading(characterId)
    try {
      await api.generateCharacterSheet(characterId)
      reload()
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setSheetLoading(null)
    }
  }

  async function handleLocationSheet(locationId: string) {
    setSheetLoading(locationId)
    try {
      await api.generateLocationSheet(locationId)
      reload()
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setSheetLoading(null)
    }
  }

  if (error && !detail) return <p className="text-sm text-red-400">{error}</p>
  if (!detail) return <p className="text-sm text-zinc-500">Cargando...</p>

  const { project, logline, chapters, characters, locations, voices } = detail

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div>
        <Link to="/" className="text-xs text-zinc-500 hover:text-zinc-300">
          &larr; Proyectos
        </Link>
        <h1 className="mt-1 text-2xl font-semibold">{project.name}</h1>
        {logline && <p className="mt-2 max-w-3xl text-sm text-zinc-400">{logline}</p>}
        <p className="mt-2 text-xs text-zinc-500">
          {project.estilo_visual} &middot; {project.tono} &middot; {project.plataformas.join(", ")} &middot; formatos:{" "}
          {project.formatos.join(", ") || "ninguno"}
        </p>
      </div>

      {error && <p className="rounded-lg border border-red-900 bg-red-950 px-3 py-2 text-sm text-red-300">{error}</p>}

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-medium">Capitulos</h2>
          <button onClick={handleNewChapter} className="rounded-lg border border-zinc-700 px-3 py-1 text-xs hover:bg-zinc-800">
            + Nuevo capitulo
          </button>
        </div>
        <ul className="divide-y divide-zinc-800 rounded-xl border border-zinc-800 bg-zinc-900">
          {chapters.map((chapter) => (
            <li key={chapter.id}>
              <Link
                to={`/chapters/${chapter.id}`}
                className="flex items-center justify-between px-4 py-3 hover:bg-zinc-800/60"
              >
                <span className="text-sm text-zinc-100">
                  {chapter.numero}. {chapter.titulo}
                </span>
                <span className={`rounded-full px-2 py-0.5 text-xs ${estadoColor[chapter.estado]}`}>
                  {estadoLabel[chapter.estado]}
                </span>
              </Link>
            </li>
          ))}
          {chapters.length === 0 && <li className="px-4 py-3 text-sm text-zinc-500">Sin capitulos importados.</li>}
        </ul>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-medium">Cast ({characters.length})</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {characters.map((character) => {
            const imageUrl = mediaUrl(character.reference_image_path)
            return (
              <div key={character.id} className="rounded-xl border border-zinc-800 bg-zinc-900 p-3 text-center">
                <div className="mx-auto mb-2 flex h-24 w-24 items-center justify-center overflow-hidden rounded-lg bg-zinc-800">
                  {imageUrl ? (
                    <img src={imageUrl} alt={character.nombre} className="h-full w-full object-cover" />
                  ) : (
                    <span className="text-xs text-zinc-600">sin ficha</span>
                  )}
                </div>
                <p className="text-sm font-medium text-zinc-100">{character.nombre}</p>
                <p className="mb-2 text-xs text-zinc-500">{character.rol}</p>
                <button
                  onClick={() => handleCharacterSheet(character.id)}
                  disabled={sheetLoading === character.id}
                  className="w-full rounded border border-zinc-700 px-2 py-1 text-xs hover:bg-zinc-800 disabled:opacity-50"
                >
                  {sheetLoading === character.id ? "Generando..." : imageUrl ? "Regenerar" : "Generar ficha"}
                </button>
              </div>
            )
          })}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-medium">Escenarios ({locations.length})</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {locations.map((location) => {
            const imageUrl = mediaUrl(location.reference_image_path)
            return (
              <div key={location.id} className="rounded-xl border border-zinc-800 bg-zinc-900 p-3 text-center">
                <div className="mx-auto mb-2 flex h-24 w-24 items-center justify-center overflow-hidden rounded-lg bg-zinc-800">
                  {imageUrl ? (
                    <img src={imageUrl} alt={location.nombre} className="h-full w-full object-cover" />
                  ) : (
                    <span className="text-xs text-zinc-600">sin ficha</span>
                  )}
                </div>
                <p className="mb-2 text-sm font-medium text-zinc-100">{location.nombre}</p>
                <button
                  onClick={() => handleLocationSheet(location.id)}
                  disabled={sheetLoading === location.id}
                  className="w-full rounded border border-zinc-700 px-2 py-1 text-xs hover:bg-zinc-800 disabled:opacity-50"
                >
                  {sheetLoading === location.id ? "Generando..." : imageUrl ? "Regenerar" : "Generar ficha"}
                </button>
              </div>
            )
          })}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-medium">Voces ({voices.length})</h2>
        <ul className="divide-y divide-zinc-800 rounded-xl border border-zinc-800 bg-zinc-900 text-sm">
          {voices.map((voice) => (
            <li key={voice.id} className="flex items-center justify-between px-4 py-2">
              <span className="text-zinc-200">{voice.personaje_id ?? "Narrador"}</span>
              <span className="text-xs text-zinc-500">
                {voice.proveedor} &middot; {voice.voice_id_externo}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
