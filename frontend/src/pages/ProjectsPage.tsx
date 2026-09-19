import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { api, type ImportSummary, type Project } from "../api/client"

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [importPath, setImportPath] = useState("")
  const [importing, setImporting] = useState(false)
  const [lastSummary, setLastSummary] = useState<ImportSummary | null>(null)

  function reload() {
    setLoading(true)
    api
      .listProjects()
      .then(setProjects)
      .catch((err) => setError(String(err.message ?? err)))
      .finally(() => setLoading(false))
  }

  useEffect(reload, [])

  async function handleImport(event: React.FormEvent) {
    event.preventDefault()
    if (!importPath.trim()) return
    setImporting(true)
    setError(null)
    try {
      const summary = await api.importProject(importPath.trim())
      setLastSummary(summary)
      setImportPath("")
      reload()
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setImporting(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Proyectos</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Historias producidas con el skill <code className="rounded bg-zinc-800 px-1 py-0.5">historias-fantasia</code>{" "}
          importadas a Estudio IA, sin copiar sus assets.
        </p>
      </div>

      <form onSubmit={handleImport} className="flex gap-2 rounded-xl border border-zinc-800 bg-zinc-900 p-4">
        <input
          value={importPath}
          onChange={(event) => setImportPath(event.target.value)}
          placeholder="C:\Users\Marco\proyectos\historias\la-bruja-del-espejo"
          className="flex-1 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-violet-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={importing}
          className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50"
        >
          {importing ? "Importando..." : "Importar carpeta"}
        </button>
      </form>

      {error && <p className="rounded-lg border border-red-900 bg-red-950 px-3 py-2 text-sm text-red-300">{error}</p>}

      {lastSummary && (
        <div className="rounded-lg border border-emerald-900 bg-emerald-950/50 px-4 py-3 text-sm text-emerald-200">
          Importado <strong>{lastSummary.name}</strong>: {lastSummary.chapters_imported} capitulos,{" "}
          {lastSummary.shots_imported} shots, {lastSummary.characters_imported} personajes,{" "}
          {lastSummary.locations_imported} escenarios, {lastSummary.assets_found} assets encontrados.
          {lastSummary.warnings.length > 0 && (
            <ul className="mt-1 list-inside list-disc text-amber-300">
              {lastSummary.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-zinc-500">Cargando...</p>
      ) : projects.length === 0 ? (
        <p className="text-sm text-zinc-500">Todavia no importaste ningun proyecto.</p>
      ) : (
        <ul className="divide-y divide-zinc-800 rounded-xl border border-zinc-800 bg-zinc-900">
          {projects.map((project) => (
            <li key={project.id}>
              <Link
                to={`/projects/${project.id}`}
                className="flex items-center justify-between px-4 py-3 hover:bg-zinc-800/60"
              >
                <div>
                  <p className="font-medium text-zinc-100">{project.name}</p>
                  <p className="text-xs text-zinc-500">
                    {project.slug} &middot; {project.estilo_visual} &middot; {project.tono}
                  </p>
                </div>
                <div className="text-xs text-zinc-500">{project.formatos.join(", ") || "sin assets"}</div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
