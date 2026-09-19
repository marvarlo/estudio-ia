import { useCallback, useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import {
  api,
  emptyShotWrite,
  mediaUrl,
  pollJob,
  shotToWrite,
  type Asset,
  type ChapterShots,
  type LintWarning,
  type Provider,
  type Shot,
  type ShotWrite,
} from "../api/client"

type GenerateKind = "image" | "audio" | "video"

export function ChapterPage() {
  const { chapterId } = useParams<{ chapterId: string }>()
  const [data, setData] = useState<ChapterShots | null>(null)
  const [edits, setEdits] = useState<Record<string, ShotWrite>>({})
  const [lint, setLint] = useState<LintWarning[]>([])
  const [error, setError] = useState<string | null>(null)
  const [savingId, setSavingId] = useState<string | null>(null)
  const [exportMessage, setExportMessage] = useState<string | null>(null)
  const [providers, setProviders] = useState<Provider[]>([])
  const [busy, setBusy] = useState<Record<string, GenerateKind | null>>({})
  const [historyFor, setHistoryFor] = useState<string | null>(null)
  const [history, setHistory] = useState<Asset[]>([])
  const [batchBusy, setBatchBusy] = useState<"image" | "audio" | null>(null)
  const [batchMessage, setBatchMessage] = useState<string | null>(null)
  const [renderBusy, setRenderBusy] = useState(false)
  const [renderMessage, setRenderMessage] = useState<string | null>(null)
  const [prose, setProse] = useState("")
  const [proseSavedPath, setProseSavedPath] = useState<string | null>(null)
  const [proseOpen, setProseOpen] = useState(false)
  const [proseBusy, setProseBusy] = useState<"write" | "save" | "derive" | null>(null)
  const [proseMessage, setProseMessage] = useState<string | null>(null)

  const load = useCallback(() => {
    if (!chapterId) return
    api
      .getChapterShots(chapterId)
      .then((result) => {
        setData(result)
        setEdits(Object.fromEntries(result.shots.map((s) => [s.id, shotToWrite(s)])))
      })
      .catch((err) => setError(String(err.message ?? err)))
    api.lintChapter(chapterId).then(setLint).catch(() => {})
    api
      .getProse(chapterId)
      .then((result) => {
        setProse(result.text)
        setProseSavedPath(result.path)
      })
      .catch(() => {})
  }, [chapterId])

  useEffect(load, [load])
  useEffect(() => {
    api.listProviders().then(setProviders).catch(() => {})
  }, [])

  const imageProviders = providers.filter((p) => p.capabilities.includes("image") && p.configured)
  const audioProviders = providers.filter((p) => p.capabilities.includes("tts") && p.configured)
  const videoProviders = providers.filter(
    (p) => (p.capabilities.includes("video_i2v") || p.capabilities.includes("video_lipsync")) && p.configured,
  )

  function updateField(shotId: string, field: keyof ShotWrite, value: ShotWrite[keyof ShotWrite]) {
    setEdits((prev) => ({ ...prev, [shotId]: { ...prev[shotId], [field]: value } }))
  }

  async function handleSave(shotId: string) {
    setSavingId(shotId)
    setError(null)
    try {
      await api.updateShot(shotId, edits[shotId])
      load()
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setSavingId(null)
    }
  }

  async function handleDelete(shotId: string) {
    setError(null)
    try {
      await api.deleteShot(shotId)
      load()
    } catch (err) {
      setError(String((err as Error).message ?? err))
    }
  }

  async function handleMove(shot: Shot, direction: -1 | 1) {
    if (!data || !chapterId) return
    const ordered = [...data.shots].sort((a, b) => a.orden - b.orden)
    const index = ordered.findIndex((s) => s.id === shot.id)
    const target = index + direction
    if (target < 0 || target >= ordered.length) return
    ;[ordered[index], ordered[target]] = [ordered[target], ordered[index]]
    try {
      await api.reorderShots(chapterId, ordered.map((s) => s.id))
      load()
    } catch (err) {
      setError(String((err as Error).message ?? err))
    }
  }

  async function handleAddShot() {
    if (!chapterId) return
    try {
      await api.createShot(chapterId, emptyShotWrite())
      load()
    } catch (err) {
      setError(String((err as Error).message ?? err))
    }
  }

  async function handleExport() {
    if (!chapterId) return
    try {
      const result = await api.exportChapter(chapterId)
      setExportMessage(`Exportado a ${result.path}`)
    } catch (err) {
      setError(String((err as Error).message ?? err))
    }
  }

  async function handleWriteProse() {
    if (!chapterId) return
    setProseBusy("write")
    setError(null)
    setProseMessage(null)
    try {
      const job = await api.generateProse(chapterId)
      const finished = await pollJob(job.id)
      if (finished.status === "failed") throw new Error(finished.error ?? "La escritura fallo")
      const result = await api.getProse(chapterId)
      setProse(result.text)
      setProseSavedPath(result.path)
      setProseMessage("Prosa escrita. Revisala antes de derivar la hoja de produccion.")
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setProseBusy(null)
    }
  }

  async function handleSaveProse() {
    if (!chapterId) return
    setProseBusy("save")
    setError(null)
    try {
      const result = await api.updateProse(chapterId, prose)
      setProseSavedPath(result.path)
      setProseMessage("Prosa guardada.")
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setProseBusy(null)
    }
  }

  async function handleDeriveSheet() {
    if (!chapterId) return
    setProseBusy("derive")
    setError(null)
    setProseMessage(null)
    try {
      const job = await api.deriveProductionSheet(chapterId)
      const finished = await pollJob(job.id)
      if (finished.status === "failed") throw new Error(finished.error ?? "La derivacion fallo")
      setProseMessage("Hoja de produccion derivada -- revisa los shots abajo.")
      load()
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setProseBusy(null)
    }
  }

  async function handleGenerate(shotId: string, kind: GenerateKind, providerId: string) {
    if (!providerId) return
    setBusy((prev) => ({ ...prev, [shotId]: kind }))
    setError(null)
    try {
      const job =
        kind === "image"
          ? await api.generateShotImage(shotId, providerId)
          : kind === "audio"
            ? await api.generateShotAudio(shotId, providerId)
            : await api.generateShotVideo(shotId, providerId)
      const finished = await pollJob(job.id)
      if (finished.status === "failed") throw new Error(finished.error ?? "El job fallo sin detalle")
      load()
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setBusy((prev) => ({ ...prev, [shotId]: null }))
    }
  }

  async function handleBatch(kind: "image" | "audio", providerId: string) {
    if (!chapterId || !providerId) return
    setBatchBusy(kind)
    setBatchMessage(null)
    setError(null)
    try {
      const result = kind === "image" ? await api.generateChapterImages(chapterId, providerId) : await api.generateChapterAudio(chapterId, providerId)
      setBatchMessage(`Encolados ${result.jobs.length} shots (${result.skipped} ya tenian ${kind === "image" ? "imagen" : "audio"} y se saltaron). Esperando...`)
      await Promise.all(result.jobs.map((job) => pollJob(job.id).catch(() => null)))
      setBatchMessage(`Lote de ${kind === "image" ? "imagenes" : "audio"} terminado: ${result.jobs.length} generados, ${result.skipped} saltados.`)
      load()
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setBatchBusy(null)
    }
  }

  async function handleRender() {
    if (!chapterId) return
    setRenderBusy(true)
    setRenderMessage(null)
    setError(null)
    try {
      const job = await api.generateChapterRender(chapterId)
      setRenderMessage("Renderizando capitulo (puede tardar varios minutos)...")
      const finished = await pollJob(job.id)
      if (finished.status === "failed") throw new Error(finished.error ?? "El render fallo sin detalle")
      setRenderMessage("Render terminado.")
      load()
    } catch (err) {
      setError(String((err as Error).message ?? err))
      setRenderMessage(null)
    } finally {
      setRenderBusy(false)
    }
  }

  async function toggleHistory(shotId: string) {
    if (historyFor === shotId) {
      setHistoryFor(null)
      return
    }
    setHistoryFor(shotId)
    try {
      setHistory(await api.listShotAssets(shotId))
    } catch (err) {
      setError(String((err as Error).message ?? err))
    }
  }

  async function handleSelectAsset(shotId: string, assetId: string) {
    try {
      await api.selectShotAsset(shotId, assetId)
      load()
    } catch (err) {
      setError(String((err as Error).message ?? err))
    }
  }

  if (error && !data) return <p className="text-sm text-red-400">{error}</p>
  if (!data) return <p className="text-sm text-zinc-500">Cargando...</p>

  const shots = [...data.shots].sort((a, b) => a.orden - b.orden)
  const chapterWarnings = lint.filter((w) => w.shot_id === null)
  const warningsByShot = new Map<string, LintWarning[]>()
  for (const warning of lint) {
    if (warning.shot_id) warningsByShot.set(warning.shot_id, [...(warningsByShot.get(warning.shot_id) ?? []), warning])
  }

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">
            Capitulo {data.chapter.numero}: {data.chapter.titulo}
          </h1>
          <p className="mt-1 text-sm text-zinc-400">{shots.length} shots</p>
        </div>
        <div className="flex shrink-0 gap-2">
          <button onClick={handleExport} className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs hover:bg-zinc-800">
            Exportar produccion.md
          </button>
          <button
            onClick={handleRender}
            disabled={renderBusy}
            className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-500 disabled:opacity-50"
          >
            {renderBusy ? "Renderizando..." : "Renderizar capitulo"}
          </button>
        </div>
      </div>

      {error && <p className="rounded-lg border border-red-900 bg-red-950 px-3 py-2 text-sm text-red-300">{error}</p>}
      {exportMessage && (
        <p className="rounded-lg border border-emerald-900 bg-emerald-950/50 px-3 py-2 text-sm text-emerald-200">{exportMessage}</p>
      )}
      {renderMessage && (
        <p className="rounded-lg border border-emerald-900 bg-emerald-950/50 px-3 py-2 text-sm text-emerald-200">{renderMessage}</p>
      )}
      {data.chapter.render_asset_path && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-3">
          <p className="mb-2 text-xs text-zinc-500">Ultimo render de este capitulo:</p>
          <video src={mediaUrl(data.chapter.render_asset_path) ?? undefined} controls className="max-h-96 w-full rounded-lg bg-black" />
        </div>
      )}
      {chapterWarnings.length > 0 && (
        <div className="rounded-lg border border-amber-900 bg-amber-950/40 px-3 py-2 text-xs text-amber-200">
          {chapterWarnings.map((w, i) => (
            <p key={i}>⚠ {w.message}</p>
          ))}
        </div>
      )}

      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-3">
        <button
          onClick={() => setProseOpen((v) => !v)}
          className="flex w-full items-center justify-between text-left text-sm font-medium text-zinc-200"
        >
          <span>Prosa del capitulo {prose ? "" : "(sin escribir)"}</span>
          <span className="text-xs text-zinc-500">{proseOpen ? "ocultar ▲" : "mostrar ▼"}</span>
        </button>
        {proseOpen && (
          <div className="mt-3 space-y-2">
            <p className="text-xs text-zinc-500">
              Escribi (o revisa/corregi) la prosa completa del capitulo antes de derivar la hoja de produccion --
              corregir tono o ritmo en texto es mas barato que descubrirlo despues de generar assets.
            </p>
            <textarea
              value={prose}
              onChange={(e) => setProse(e.target.value)}
              rows={12}
              placeholder="Todavia no hay prosa -- generala o pegala aca."
              className="w-full rounded border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm leading-relaxed"
            />
            {proseMessage && <p className="text-xs text-emerald-300">{proseMessage}</p>}
            <div className="flex flex-wrap gap-2">
              <button
                onClick={handleWriteProse}
                disabled={proseBusy !== null}
                className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-500 disabled:opacity-50"
              >
                {proseBusy === "write" ? "Escribiendo..." : prose ? "Re-escribir con IA" : "Escribir con IA"}
              </button>
              <button
                onClick={handleSaveProse}
                disabled={proseBusy !== null}
                className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs hover:bg-zinc-800 disabled:opacity-50"
              >
                {proseBusy === "save" ? "Guardando..." : "Guardar cambios"}
              </button>
              <button
                onClick={handleDeriveSheet}
                disabled={proseBusy !== null || !proseSavedPath}
                className="rounded-lg bg-emerald-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-600 disabled:opacity-50"
                title={!proseSavedPath ? "Escribi o guarda la prosa primero" : undefined}
              >
                {proseBusy === "derive" ? "Derivando..." : "Derivar hoja de produccion"}
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-zinc-800 bg-zinc-900 p-3 text-xs">
        <span className="text-zinc-400">Generar por lote:</span>
        <BatchButton label="Imagenes" providers={imageProviders} busy={batchBusy === "image"} onRun={(pid) => handleBatch("image", pid)} />
        <BatchButton label="Audio" providers={audioProviders} busy={batchBusy === "audio"} onRun={(pid) => handleBatch("audio", pid)} />
        {batchMessage && <span className="text-zinc-400">{batchMessage}</span>}
      </div>

      <div className="space-y-3">
        {shots.map((shot, index) => {
          const edit = edits[shot.id] ?? shotToWrite(shot)
          const imageUrl = mediaUrl(shot.image_asset_path)
          const audioUrl = mediaUrl(shot.audio_asset_path)
          const videoUrl = mediaUrl(shot.video_asset_path)
          const shotWarnings = warningsByShot.get(shot.id) ?? []
          const shotBusy = busy[shot.id];

          return (
            <div key={shot.id} className="flex gap-4 rounded-xl border border-zinc-800 bg-zinc-900 p-4">
              <div className="flex w-44 shrink-0 flex-col gap-2">
                <div className="flex h-24 w-full items-center justify-center overflow-hidden rounded-lg bg-zinc-800">
                  {videoUrl ? (
                    <video src={videoUrl} controls className="h-full w-full object-cover" />
                  ) : imageUrl ? (
                    <img src={imageUrl} alt={`Shot ${shot.orden}`} className="h-full w-full object-cover" />
                  ) : (
                    <span className="text-xs text-zinc-600">sin imagen</span>
                  )}
                </div>
                <div className="flex justify-between text-xs text-zinc-500">
                  <button onClick={() => handleMove(shot, -1)} disabled={index === 0} className="hover:text-white disabled:opacity-30">
                    ↑ subir
                  </button>
                  <button
                    onClick={() => handleMove(shot, 1)}
                    disabled={index === shots.length - 1}
                    className="hover:text-white disabled:opacity-30"
                  >
                    bajar ↓
                  </button>
                </div>
                {audioUrl && (
                  <audio controls src={audioUrl} className="h-7 w-full">
                    <track kind="captions" />
                  </audio>
                )}
                <button onClick={() => toggleHistory(shot.id)} className="text-xs text-zinc-500 underline hover:text-zinc-300">
                  {historyFor === shot.id ? "Ocultar historial" : "Ver historial"}
                </button>
              </div>

              <div className="min-w-0 flex-1 space-y-2">
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-zinc-400">#{shot.orden}</span>
                  <select
                    value={edit.tipo}
                    onChange={(e) => updateField(shot.id, "tipo", e.target.value)}
                    className="rounded border border-zinc-700 bg-zinc-950 px-1.5 py-0.5"
                  >
                    <option value="Narracion">Narracion</option>
                    <option value="Dialogo">Dialogo</option>
                  </select>
                  <input
                    value={edit.personaje_ids.join(", ")}
                    onChange={(e) =>
                      updateField(
                        shot.id,
                        "personaje_ids",
                        e.target.value
                          .split(",")
                          .map((s) => s.trim())
                          .filter(Boolean),
                      )
                    }
                    placeholder="personajes (coma)"
                    className="w-40 rounded border border-zinc-700 bg-zinc-950 px-1.5 py-0.5"
                  />
                  <input
                    value={edit.escenario_id ?? ""}
                    onChange={(e) => updateField(shot.id, "escenario_id", e.target.value || null)}
                    placeholder="escenario_id"
                    className="w-32 rounded border border-zinc-700 bg-zinc-950 px-1.5 py-0.5"
                  />
                  <input
                    value={edit.momento_dia}
                    onChange={(e) => updateField(shot.id, "momento_dia", e.target.value)}
                    placeholder="momento del dia"
                    className="w-28 rounded border border-zinc-700 bg-zinc-950 px-1.5 py-0.5"
                  />
                  <input
                    type="number"
                    value={edit.duracion_estimada_seg ?? ""}
                    onChange={(e) => updateField(shot.id, "duracion_estimada_seg", e.target.value ? Number(e.target.value) : null)}
                    placeholder="seg"
                    className="w-16 rounded border border-zinc-700 bg-zinc-950 px-1.5 py-0.5"
                  />
                </div>

                <textarea
                  value={edit.texto}
                  onChange={(e) => updateField(shot.id, "texto", e.target.value)}
                  rows={2}
                  placeholder="Texto narrado/dialogo"
                  className="w-full rounded border border-zinc-700 bg-zinc-950 px-2 py-1 text-sm"
                />
                <textarea
                  value={edit.prompt_imagen}
                  onChange={(e) => updateField(shot.id, "prompt_imagen", e.target.value)}
                  rows={2}
                  placeholder="Prompt de imagen"
                  className="w-full rounded border border-zinc-700 bg-zinc-950 px-2 py-1 text-xs text-zinc-400"
                />

                {shotWarnings.length > 0 && (
                  <div className="text-xs text-amber-300">
                    {shotWarnings.map((w, i) => (
                      <p key={i}>⚠ {w.message}</p>
                    ))}
                  </div>
                )}

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => handleSave(shot.id)}
                    disabled={savingId === shot.id}
                    className="rounded-lg bg-violet-600 px-3 py-1 text-xs font-medium text-white hover:bg-violet-500 disabled:opacity-50"
                  >
                    {savingId === shot.id ? "Guardando..." : "Guardar"}
                  </button>
                  <button
                    onClick={() => handleDelete(shot.id)}
                    className="rounded-lg border border-red-900 px-3 py-1 text-xs text-red-300 hover:bg-red-950"
                  >
                    Eliminar
                  </button>
                  <span className="mx-1 h-4 w-px bg-zinc-700" />
                  <GenerateControl
                    label="Imagen"
                    providers={imageProviders}
                    busy={shotBusy === "image"}
                    onRun={(pid) => handleGenerate(shot.id, "image", pid)}
                  />
                  <GenerateControl
                    label="Audio"
                    providers={audioProviders}
                    busy={shotBusy === "audio"}
                    onRun={(pid) => handleGenerate(shot.id, "audio", pid)}
                  />
                  <GenerateControl
                    label="Video"
                    providers={videoProviders}
                    busy={shotBusy === "video"}
                    onRun={(pid) => handleGenerate(shot.id, "video", pid)}
                    disabled={!shot.image_asset_path}
                    disabledTitle="Genera la imagen primero"
                  />
                </div>

                {historyFor === shot.id && (
                  <div className="mt-2 rounded-lg border border-zinc-800 bg-zinc-950 p-2">
                    <p className="mb-1 text-xs text-zinc-500">Historial de versiones ({history.length}):</p>
                    <div className="flex flex-wrap gap-2">
                      {history.map((asset) => {
                        const isSelected = [shot.image_asset_path, shot.audio_asset_path, shot.video_asset_path].includes(asset.path)
                        const thumbUrl = mediaUrl(asset.path)
                        return (
                          <button
                            key={asset.id}
                            onClick={() => handleSelectAsset(shot.id, asset.id)}
                            className={`rounded border px-1.5 py-1 text-left text-xs ${isSelected ? "border-violet-500 bg-violet-950/40" : "border-zinc-700 hover:bg-zinc-800"}`}
                            title={asset.path}
                          >
                            {asset.kind === "image" && thumbUrl ? (
                              <img src={thumbUrl} alt="" className="mb-1 h-14 w-20 rounded object-cover" />
                            ) : (
                              <span className="mb-1 block h-14 w-20 rounded bg-zinc-800 text-center leading-[3.5rem]">{asset.kind}</span>
                            )}
                            <span className="block text-[10px] text-zinc-500">{asset.provider || "importado"}</span>
                          </button>
                        )
                      })}
                      {history.length === 0 && <p className="text-xs text-zinc-600">Sin generaciones todavia.</p>}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      <button onClick={handleAddShot} className="w-full rounded-xl border border-dashed border-zinc-700 py-3 text-sm text-zinc-400 hover:bg-zinc-900">
        + Agregar shot
      </button>
    </div>
  )
}

function GenerateControl({
  label,
  providers,
  busy,
  onRun,
  disabled,
  disabledTitle,
}: {
  label: string
  providers: Provider[]
  busy: boolean
  onRun: (providerId: string) => void
  disabled?: boolean
  disabledTitle?: string
}) {
  const [providerId, setProviderId] = useState("")
  useEffect(() => {
    if (!providerId && providers.length > 0) setProviderId(providers[0].id)
  }, [providers, providerId])

  if (providers.length === 0) return null

  return (
    <span className="flex items-center gap-1" title={disabled ? disabledTitle : undefined}>
      <select
        value={providerId}
        onChange={(e) => setProviderId(e.target.value)}
        disabled={disabled}
        className="rounded border border-zinc-700 bg-zinc-950 px-1 py-1 text-xs disabled:opacity-40"
      >
        {providers.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>
      <button
        onClick={() => onRun(providerId)}
        disabled={busy || disabled || !providerId}
        className="rounded border border-zinc-700 px-2 py-1 text-xs hover:bg-zinc-800 disabled:opacity-40"
      >
        {busy ? `${label}...` : label}
      </button>
    </span>
  )
}

function BatchButton({
  label,
  providers,
  busy,
  onRun,
}: {
  label: string
  providers: Provider[]
  busy: boolean
  onRun: (providerId: string) => void
}) {
  const [providerId, setProviderId] = useState("")
  useEffect(() => {
    if (!providerId && providers.length > 0) setProviderId(providers[0].id)
  }, [providers, providerId])

  if (providers.length === 0) return null

  return (
    <span className="flex items-center gap-1">
      <select value={providerId} onChange={(e) => setProviderId(e.target.value)} className="rounded border border-zinc-700 bg-zinc-950 px-1 py-1">
        {providers.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>
      <button
        onClick={() => onRun(providerId)}
        disabled={busy || !providerId}
        className="rounded bg-violet-600 px-2 py-1 font-medium text-white hover:bg-violet-500 disabled:opacity-50"
      >
        {busy ? `Generando ${label}...` : `Generar ${label}`}
      </button>
    </span>
  )
}
