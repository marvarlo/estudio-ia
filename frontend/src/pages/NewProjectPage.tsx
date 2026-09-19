import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { api, mediaUrl, type Canon, type Character, type Location, type Project, type Provider, type VoicePoolVoice } from "../api/client"

type Step = 1 | 2 | 3 | 4

const STEP_LABELS: Record<Step, string> = {
  1: "1. Contenido",
  2: "2. Canon",
  3: "3. Cast",
  4: "4. Voces",
}

function StepBar({ step }: { step: Step }) {
  return (
    <div className="mb-6 flex gap-2 text-xs">
      {([1, 2, 3, 4] as Step[]).map((s) => (
        <span
          key={s}
          className={`rounded-full px-3 py-1 ${s === step ? "bg-violet-600 text-white" : s < step ? "bg-emerald-900 text-emerald-200" : "bg-zinc-800 text-zinc-500"}`}
        >
          {STEP_LABELS[s]}
        </span>
      ))}
    </div>
  )
}

export function NewProjectPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>(1)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [textProviders, setTextProviders] = useState<Provider[]>([])

  const [project, setProject] = useState<Project | null>(null)
  const [canon, setCanon] = useState<Canon | null>(null)
  const [characters, setCharacters] = useState<Character[]>([])
  const [locations, setLocations] = useState<Location[]>([])
  const [voicePool, setVoicePool] = useState<VoicePoolVoice[]>([])
  const [sheetLoading, setSheetLoading] = useState<string | null>(null)

  // Paso 1 -- brief
  const [name, setName] = useState("")
  const [estiloNarrativo, setEstiloNarrativo] = useState("renacimiento/regresion")
  const [tono, setTono] = useState("NORMAL")
  const [estiloVisual, setEstiloVisual] = useState("anime")
  const [numEpisodios, setNumEpisodios] = useState(10)
  const [duracionObjetivo, setDuracionObjetivo] = useState(10)
  const [semilla, setSemilla] = useState("")
  const [providerId, setProviderId] = useState("lemonade-text")

  // Paso 3 -- cast brief
  const [numPersonajes, setNumPersonajes] = useState(5)
  const [numEscenarios, setNumEscenarios] = useState(4)
  const [notasCast, setNotasCast] = useState("")

  // Paso 4 -- nueva voz de pool
  const [nuevaVozProveedor, setNuevaVozProveedor] = useState("ElevenLabs")
  const [nuevaVozId, setNuevaVozId] = useState("")
  const [nuevaVozNombre, setNuevaVozNombre] = useState("")

  useEffect(() => {
    api
      .listProviders()
      .then((all) => setTextProviders(all.filter((p) => p.capabilities.includes("text"))))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (step === 4) {
      api.listVoicePool().then(setVoicePool).catch(() => {})
    }
  }, [step])

  async function handleCreateAndGenerateCanon(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const createdProject = await api.createProject({ name, estilo_visual: estiloVisual, tono, plataformas: ["YouTube"] })
      setProject(createdProject)
      const generatedCanon = await api.generateCanon(createdProject.id, {
        estilo_narrativo: estiloNarrativo,
        tono,
        plataformas: ["YouTube"],
        estilo_visual: estiloVisual,
        num_episodios: numEpisodios,
        duracion_objetivo_min: duracionObjetivo,
        semilla,
        provider_id: providerId,
      })
      setCanon(generatedCanon)
      setStep(2)
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setBusy(false)
    }
  }

  async function handleRegenerateCanon() {
    if (!project) return
    setBusy(true)
    setError(null)
    try {
      const generatedCanon = await api.generateCanon(project.id, {
        estilo_narrativo: estiloNarrativo,
        tono,
        plataformas: ["YouTube"],
        estilo_visual: estiloVisual,
        num_episodios: numEpisodios,
        duracion_objetivo_min: duracionObjetivo,
        semilla,
        provider_id: providerId,
      })
      setCanon(generatedCanon)
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setBusy(false)
    }
  }

  async function handleGenerateCast(event: React.FormEvent) {
    event.preventDefault()
    if (!project) return
    setBusy(true)
    setError(null)
    try {
      const result = await api.generateCast(project.id, {
        num_personajes: numPersonajes,
        num_escenarios: numEscenarios,
        notas: notasCast,
        provider_id: providerId,
      })
      setCharacters(result.characters)
      setLocations(result.locations)
      setStep(4)
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setBusy(false)
    }
  }

  async function handleGenerateCharacterSheet(character: Character) {
    setSheetLoading(character.id)
    setError(null)
    try {
      await api.generateCharacterSheet(character.id)
      const detail = await api.getProject(project!.id)
      setCharacters(detail.characters)
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setSheetLoading(null)
    }
  }

  async function handleGenerateLocationSheet(location: Location) {
    setSheetLoading(location.id)
    setError(null)
    try {
      await api.generateLocationSheet(location.id)
      const detail = await api.getProject(project!.id)
      setLocations(detail.locations)
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setSheetLoading(null)
    }
  }

  async function handleAddVoice(event: React.FormEvent) {
    event.preventDefault()
    if (!nuevaVozId.trim()) return
    try {
      await api.addVoiceToPool({
        proveedor: nuevaVozProveedor,
        voice_id_externo: nuevaVozId.trim(),
        nombre_interno: nuevaVozNombre.trim(),
      })
      setNuevaVozId("")
      setNuevaVozNombre("")
      setVoicePool(await api.listVoicePool())
    } catch (err) {
      setError(String((err as Error).message ?? err))
    }
  }

  async function handleAssignAndFinish() {
    if (!project) return
    setBusy(true)
    setError(null)
    try {
      await api.assignVoices(project.id)
      const chapter = await api.createChapter(project.id, "Capítulo 1")
      navigate(`/chapters/${chapter.id}`)
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="mb-1 text-2xl font-semibold">Nuevo proyecto</h1>
      <p className="mb-4 text-sm text-zinc-400">Wizard de contenido y cast (fase 1) -- ver SKILL.md pasos 1-8.</p>
      <StepBar step={step} />

      {error && (
        <p className="mb-4 rounded-lg border border-red-900 bg-red-950 px-3 py-2 text-sm text-red-300">{error}</p>
      )}

      {step === 1 && (
        <form onSubmit={handleCreateAndGenerateCanon} className="space-y-4 rounded-xl border border-zinc-800 bg-zinc-900 p-5">
          <div>
            <label className="mb-1 block text-xs text-zinc-400">Nombre de la historia</label>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
              placeholder="El Faro de las Mareas Rotas"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs text-zinc-400">Estilo narrativo</label>
              <input
                value={estiloNarrativo}
                onChange={(e) => setEstiloNarrativo(e.target.value)}
                className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
                placeholder="isekai + venganza, renacimiento, sistema..."
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-zinc-400">Estilo visual</label>
              <input
                value={estiloVisual}
                onChange={(e) => setEstiloVisual(e.target.value)}
                className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-zinc-400">Tono</label>
              <select
                value={tono}
                onChange={(e) => setTono(e.target.value)}
                className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
              >
                <option value="NORMAL">NORMAL</option>
                <option value="SAFE">SAFE</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-zinc-400">Proveedor de escritura</label>
              <select
                value={providerId}
                onChange={(e) => setProviderId(e.target.value)}
                className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
              >
                {textProviders.map((p) => (
                  <option key={p.id} value={p.id} disabled={!p.configured}>
                    {p.name} {p.configured ? "" : "(sin configurar)"}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-zinc-400">Numero de episodios</label>
              <input
                type="number"
                min={1}
                value={numEpisodios}
                onChange={(e) => setNumEpisodios(Number(e.target.value))}
                className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-zinc-400">Duracion objetivo (min/episodio)</label>
              <input
                type="number"
                min={1}
                value={duracionObjetivo}
                onChange={(e) => setDuracionObjetivo(Number(e.target.value))}
                className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs text-zinc-400">
              Semilla de historia (opcional -- dejar vacio para una premisa original)
            </label>
            <textarea
              value={semilla}
              onChange={(e) => setSemilla(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
            />
          </div>
          <button
            type="submit"
            disabled={busy}
            className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50"
          >
            {busy ? "Generando canon..." : "Crear proyecto y generar canon"}
          </button>
        </form>
      )}

      {step === 2 && canon && (
        <div className="space-y-4">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
            <h2 className="mb-2 text-lg font-medium">Logline</h2>
            <p className="text-sm text-zinc-200">{canon.logline}</p>
            <h2 className="mb-2 mt-4 text-lg font-medium">Premisa</h2>
            <p className="text-sm text-zinc-300">{canon.premisa}</p>
            <h2 className="mb-2 mt-4 text-lg font-medium">Reglas del sistema</h2>
            <p className="whitespace-pre-wrap text-sm text-zinc-300">{canon.reglas_sistema}</p>
            <h2 className="mb-2 mt-4 text-lg font-medium">Esqueleto de temporada</h2>
            <ul className="space-y-2 text-sm">
              {canon.temporada.map((ep) => (
                <li key={ep.numero} className="rounded-lg bg-zinc-800/60 p-2">
                  <span className="font-medium">Cap. {ep.numero}:</span> {ep.resumen}
                  <br />
                  <span className="text-xs text-zinc-500">Cliffhanger: {ep.cliffhanger}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleRegenerateCanon}
              disabled={busy}
              className="rounded-lg border border-zinc-700 px-4 py-2 text-sm hover:bg-zinc-800 disabled:opacity-50"
            >
              {busy ? "Regenerando..." : "Regenerar canon"}
            </button>
            <button
              onClick={() => setStep(3)}
              className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500"
            >
              Continuar a Cast
            </button>
          </div>
        </div>
      )}

      {step === 3 && (
        <form onSubmit={handleGenerateCast} className="space-y-4 rounded-xl border border-zinc-800 bg-zinc-900 p-5">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs text-zinc-400">Numero de personajes</label>
              <input
                type="number"
                min={1}
                value={numPersonajes}
                onChange={(e) => setNumPersonajes(Number(e.target.value))}
                className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-zinc-400">Numero de escenarios</label>
              <input
                type="number"
                min={1}
                value={numEscenarios}
                onChange={(e) => setNumEscenarios(Number(e.target.value))}
                className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs text-zinc-400">Notas adicionales (opcional)</label>
            <textarea
              value={notasCast}
              onChange={(e) => setNotasCast(e.target.value)}
              rows={2}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
            />
          </div>
          <button
            type="submit"
            disabled={busy}
            className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50"
          >
            {busy ? "Generando cast..." : "Generar personajes y escenarios"}
          </button>
        </form>
      )}

      {step === 4 && (
        <div className="space-y-6">
          <section>
            <h2 className="mb-3 text-lg font-medium">Personajes ({characters.length})</h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {characters.map((c) => {
                const imageUrl = mediaUrl(c.reference_image_path)
                return (
                  <div key={c.id} className="rounded-xl border border-zinc-800 bg-zinc-900 p-3">
                    <div className="mb-2 flex h-28 w-full items-center justify-center overflow-hidden rounded-lg bg-zinc-800">
                      {imageUrl ? (
                        <img src={imageUrl} alt={c.nombre} className="h-full w-full object-cover" />
                      ) : (
                        <span className="text-xs text-zinc-600">sin ficha</span>
                      )}
                    </div>
                    <p className="text-sm font-medium">{c.nombre}</p>
                    <p className="mb-2 text-xs text-zinc-500">
                      {c.slug} &middot; {c.rol}
                    </p>
                    <button
                      onClick={() => handleGenerateCharacterSheet(c)}
                      disabled={sheetLoading === c.id}
                      className="w-full rounded-lg border border-zinc-700 px-2 py-1 text-xs hover:bg-zinc-800 disabled:opacity-50"
                    >
                      {sheetLoading === c.id ? "Generando..." : imageUrl ? "Regenerar ficha" : "Generar ficha"}
                    </button>
                  </div>
                )
              })}
            </div>
          </section>

          <section>
            <h2 className="mb-3 text-lg font-medium">Escenarios ({locations.length})</h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {locations.map((l) => {
                const imageUrl = mediaUrl(l.reference_image_path)
                return (
                  <div key={l.id} className="rounded-xl border border-zinc-800 bg-zinc-900 p-3">
                    <div className="mb-2 flex h-28 w-full items-center justify-center overflow-hidden rounded-lg bg-zinc-800">
                      {imageUrl ? (
                        <img src={imageUrl} alt={l.nombre} className="h-full w-full object-cover" />
                      ) : (
                        <span className="text-xs text-zinc-600">sin ficha</span>
                      )}
                    </div>
                    <p className="text-sm font-medium">{l.nombre}</p>
                    <p className="mb-2 text-xs text-zinc-500">{l.slug}</p>
                    <button
                      onClick={() => handleGenerateLocationSheet(l)}
                      disabled={sheetLoading === l.id}
                      className="w-full rounded-lg border border-zinc-700 px-2 py-1 text-xs hover:bg-zinc-800 disabled:opacity-50"
                    >
                      {sheetLoading === l.id ? "Generando..." : imageUrl ? "Regenerar ficha" : "Generar ficha"}
                    </button>
                  </div>
                )
              })}
            </div>
          </section>

          <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
            <h2 className="mb-3 text-lg font-medium">Pool de voces del canal</h2>
            <ul className="mb-3 space-y-1 text-sm">
              {voicePool.map((v) => (
                <li key={v.id} className="flex justify-between rounded bg-zinc-800/60 px-2 py-1">
                  <span>
                    {v.nombre_interno || v.voice_id_externo} ({v.proveedor})
                  </span>
                  <span className="text-xs text-zinc-500">usada {v.veces_usada}x</span>
                </li>
              ))}
              {voicePool.length === 0 && <li className="text-xs text-zinc-500">Pool vacio -- agrega al menos una voz.</li>}
            </ul>
            <form onSubmit={handleAddVoice} className="flex flex-wrap gap-2">
              <select
                value={nuevaVozProveedor}
                onChange={(e) => setNuevaVozProveedor(e.target.value)}
                className="rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-1.5 text-xs"
              >
                <option>ElevenLabs</option>
                <option>Lemonade</option>
              </select>
              <input
                value={nuevaVozId}
                onChange={(e) => setNuevaVozId(e.target.value)}
                placeholder="voice_id externo"
                className="flex-1 rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-1.5 text-xs"
              />
              <input
                value={nuevaVozNombre}
                onChange={(e) => setNuevaVozNombre(e.target.value)}
                placeholder="nombre interno (opcional)"
                className="flex-1 rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-1.5 text-xs"
              />
              <button type="submit" className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs hover:bg-zinc-800">
                Agregar
              </button>
            </form>
          </section>

          <button
            onClick={handleAssignAndFinish}
            disabled={busy || voicePool.length === 0}
            className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50"
          >
            {busy ? "Asignando..." : "Asignar voces, crear Capitulo 1 y abrir editor"}
          </button>
        </div>
      )}
    </div>
  )
}
