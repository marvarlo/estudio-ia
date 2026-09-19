import { useCallback, useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { api, mediaUrl, pollJob, type ChapterShots, type LyricLine, type Shot, type TrackProjectResult } from "../api/client"

export function TrackPage() {
  const { trackId } = useParams<{ trackId: string }>()
  const [data, setData] = useState<TrackProjectResult | null>(null)
  const [lines, setLines] = useState<LyricLine[]>([])
  const [chapterShots, setChapterShots] = useState<ChapterShots | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const load = useCallback(() => {
    if (!trackId) return
    api.getTrack(trackId).then(setData).catch((err) => setError(String(err.message ?? err)))
    api.listLyricLines(trackId).then(setLines).catch(() => {})
  }, [trackId])

  useEffect(load, [load])

  useEffect(() => {
    if (!data) return
    api.getChapterShots(data.chapter.id).then(setChapterShots).catch(() => {})
  }, [data])

  async function handleTranscribe() {
    if (!trackId) return
    setBusy("transcribe")
    setError(null)
    try {
      const job = await api.transcribeTrack(trackId)
      const finished = await pollJob(job.id)
      if (finished.status === "failed") throw new Error(finished.error ?? "La transcripcion fallo")
      load()
      setMessage("Letra transcrita.")
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setBusy(null)
    }
  }

  async function handleUpdateLine(line: LyricLine, field: "text" | "start" | "end", value: string) {
    const updated = { text: line.text, start: line.start, end: line.end, [field]: field === "text" ? value : Number(value) }
    try {
      const saved = await api.updateLyricLine(line.id, updated)
      setLines((prev) => prev.map((l) => (l.id === line.id ? saved : l)))
    } catch (err) {
      setError(String((err as Error).message ?? err))
    }
  }

  async function handleDeleteLine(lineId: string) {
    try {
      await api.deleteLyricLine(lineId)
      setLines((prev) => prev.filter((l) => l.id !== lineId))
    } catch (err) {
      setError(String((err as Error).message ?? err))
    }
  }

  async function handleGenerateShots() {
    if (!trackId || !data) return
    setBusy("shots")
    setError(null)
    try {
      await api.generateShotsFromLyrics(trackId)
      const shots = await api.getChapterShots(data.chapter.id)
      setChapterShots(shots)
      setMessage(`${shots.shots.length} shots generados a partir de la letra.`)
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setBusy(null)
    }
  }

  async function handleGenerateBackgrounds() {
    if (!data) return
    setBusy("backgrounds")
    setError(null)
    try {
      const result = await api.generateChapterImages(data.chapter.id, "lemonade-image")
      await Promise.all(result.jobs.map((job) => pollJob(job.id).catch(() => null)))
      const shots = await api.getChapterShots(data.chapter.id)
      setChapterShots(shots)
      setMessage(`Fondos generados: ${result.jobs.length} nuevos, ${result.skipped} ya tenian uno.`)
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setBusy(null)
    }
  }

  async function handleGenerateOneBackground(shot: Shot) {
    setBusy(`shot-${shot.id}`)
    setError(null)
    try {
      const job = await api.generateShotImage(shot.id, "lemonade-image")
      const finished = await pollJob(job.id)
      if (finished.status === "failed") throw new Error(finished.error ?? "Fallo la generacion")
      if (data) setChapterShots(await api.getChapterShots(data.chapter.id))
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setBusy(null)
    }
  }

  async function handleRender(compositionId: "LyricsVideo" | "Karaoke") {
    if (!trackId) return
    setBusy(`render-${compositionId}`)
    setError(null)
    setMessage(null)
    try {
      const job = await api.renderMusicVideo(trackId, compositionId)
      setMessage(`Renderizando ${compositionId}...`)
      const finished = await pollJob(job.id)
      if (finished.status === "failed") throw new Error(finished.error ?? "El render fallo")
      setMessage("Render terminado.")
      load()
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setBusy(null)
    }
  }

  if (error && !data) return <p className="text-sm text-red-400">{error}</p>
  if (!data) return <p className="text-sm text-zinc-500">Cargando...</p>

  const sortedLines = [...lines].sort((a, b) => a.start - b.start)
  const shots = chapterShots ? [...chapterShots.shots].sort((a, b) => a.orden - b.orden) : []
  const renderPath = chapterShots?.chapter.render_asset_path ?? null

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{data.project.name}</h1>
        <p className="mt-1 text-sm text-zinc-400">
          {data.project.kind === "karaoke" ? "Karaoke" : "Lyrics video"} &middot;{" "}
          {data.track.duration_seconds ? `${data.track.duration_seconds.toFixed(1)}s` : "duracion desconocida"}
        </p>
      </div>

      {error && <p className="rounded-lg border border-red-900 bg-red-950 px-3 py-2 text-sm text-red-300">{error}</p>}
      {message && (
        <p className="rounded-lg border border-emerald-900 bg-emerald-950/50 px-3 py-2 text-sm text-emerald-200">{message}</p>
      )}

      <section className="space-y-3 rounded-xl border border-zinc-800 bg-zinc-900 p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-zinc-200">1. Letra transcrita ({sortedLines.length} lineas)</h2>
          <button
            onClick={handleTranscribe}
            disabled={busy === "transcribe"}
            className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-500 disabled:opacity-50"
          >
            {busy === "transcribe" ? "Transcribiendo..." : sortedLines.length > 0 ? "Re-transcribir" : "Transcribir"}
          </button>
        </div>
        <div className="space-y-1">
          {sortedLines.map((line) => (
            <div key={line.id} className="flex items-center gap-2 rounded border border-zinc-800 bg-zinc-950 px-2 py-1 text-xs">
              <input
                type="number"
                step="0.1"
                defaultValue={line.start}
                onBlur={(e) => handleUpdateLine(line, "start", e.target.value)}
                className="w-16 rounded border border-zinc-700 bg-zinc-900 px-1 py-0.5"
              />
              <input
                type="number"
                step="0.1"
                defaultValue={line.end}
                onBlur={(e) => handleUpdateLine(line, "end", e.target.value)}
                className="w-16 rounded border border-zinc-700 bg-zinc-900 px-1 py-0.5"
              />
              <input
                defaultValue={line.text}
                onBlur={(e) => handleUpdateLine(line, "text", e.target.value)}
                className="min-w-0 flex-1 rounded border border-zinc-700 bg-zinc-900 px-2 py-0.5"
              />
              {line.words.some((w) => w.suspect) && <span title="Palabra de baja confianza -- revisar">⚠</span>}
              <button onClick={() => handleDeleteLine(line.id)} className="text-red-400 hover:text-red-300">
                Eliminar
              </button>
            </div>
          ))}
          {sortedLines.length === 0 && <p className="text-xs text-zinc-600">Todavia no hay letra transcrita.</p>}
        </div>
      </section>

      <section className="space-y-3 rounded-xl border border-zinc-800 bg-zinc-900 p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-zinc-200">2. Shots ({shots.length})</h2>
          <div className="flex gap-2">
            <button
              onClick={handleGenerateShots}
              disabled={busy === "shots" || sortedLines.length === 0}
              className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs hover:bg-zinc-800 disabled:opacity-50"
            >
              {busy === "shots" ? "Generando..." : "Generar shots desde la letra"}
            </button>
            <button
              onClick={handleGenerateBackgrounds}
              disabled={busy === "backgrounds" || shots.length === 0}
              className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-500 disabled:opacity-50"
            >
              {busy === "backgrounds" ? "Generando fondos..." : "Generar todos los fondos"}
            </button>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {shots.map((shot) => {
            const imageUrl = mediaUrl(shot.image_asset_path)
            return (
              <div key={shot.id} className="space-y-1 rounded-lg border border-zinc-800 bg-zinc-950 p-2">
                <div className="flex h-20 items-center justify-center overflow-hidden rounded bg-zinc-900">
                  {imageUrl ? (
                    <img src={imageUrl} alt="" className="h-full w-full object-cover" />
                  ) : (
                    <span className="text-[10px] text-zinc-600">sin fondo</span>
                  )}
                </div>
                <p className="line-clamp-2 text-[11px] text-zinc-400">{shot.texto}</p>
                <button
                  onClick={() => handleGenerateOneBackground(shot)}
                  disabled={busy === `shot-${shot.id}`}
                  className="w-full rounded border border-zinc-700 py-1 text-[11px] hover:bg-zinc-800 disabled:opacity-50"
                >
                  {busy === `shot-${shot.id}` ? "..." : imageUrl ? "Regenerar" : "Generar fondo"}
                </button>
              </div>
            )
          })}
          {shots.length === 0 && <p className="col-span-full text-xs text-zinc-600">Todavia no hay shots.</p>}
        </div>
      </section>

      <section className="space-y-3 rounded-xl border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="text-sm font-semibold text-zinc-200">3. Render</h2>
        <div className="flex gap-2">
          <button
            onClick={() => handleRender("LyricsVideo")}
            disabled={busy === "render-LyricsVideo" || shots.length === 0}
            className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-500 disabled:opacity-50"
          >
            {busy === "render-LyricsVideo" ? "Renderizando..." : "Renderizar Lyrics Video"}
          </button>
          <button
            onClick={() => handleRender("Karaoke")}
            disabled={busy === "render-Karaoke" || shots.length === 0}
            className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-500 disabled:opacity-50"
          >
            {busy === "render-Karaoke" ? "Renderizando..." : "Renderizar Karaoke"}
          </button>
        </div>
        {renderPath && (
          <video src={mediaUrl(renderPath) ?? undefined} controls className="max-h-96 w-full rounded-lg bg-black" />
        )}
      </section>
    </div>
  )
}
