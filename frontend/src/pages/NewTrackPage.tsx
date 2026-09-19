import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { api } from "../api/client"

// Wizard de musica (fase 4): a diferencia de una historia (4 pasos, varias
// paginas), crear una pista es un solo formulario -- subir el audio y elegir
// el tipo de producto ya alcanza para arrancar el pipeline (transcribir,
// editar letra, generar fondos, renderizar) en TrackPage.
export function NewTrackPage() {
  const navigate = useNavigate()
  const [name, setName] = useState("")
  const [kind, setKind] = useState<"lyrics_video" | "karaoke">("lyrics_video")
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file || !name.trim()) return
    setBusy(true)
    setError(null)
    try {
      const result = await api.createTrack({ name: name.trim(), kind, file })
      navigate(`/tracks/${result.track.id}`)
    } catch (err) {
      setError(String((err as Error).message ?? err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-4">
      <h1 className="text-2xl font-semibold">Nuevo videoclip de letra / karaoke</h1>
      <p className="text-sm text-zinc-400">
        Subi un MP3/WAV -- el pipeline transcribe la letra con timestamps reales, genera un fondo por
        linea, y renderiza un video con la letra sincronizada (con resaltado de palabra a palabra en
        modo Karaoke).
      </p>
      <form onSubmit={handleSubmit} className="space-y-4 rounded-xl border border-zinc-800 bg-zinc-900 p-5">
        <div>
          <label className="mb-1 block text-xs text-zinc-400">Nombre de la cancion</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="ej. Noches en B-Wing"
            className="w-full rounded border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-zinc-400">Tipo de producto</label>
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value as "lyrics_video" | "karaoke")}
            className="w-full rounded border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
          >
            <option value="lyrics_video">Lyrics video (letra sincronizada)</option>
            <option value="karaoke">Karaoke (resaltado palabra a palabra)</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-zinc-400">Archivo de audio (MP3/WAV)</label>
          <input
            type="file"
            accept="audio/*"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="w-full text-sm"
          />
        </div>
        {error && <p className="rounded-lg border border-red-900 bg-red-950 px-3 py-2 text-sm text-red-300">{error}</p>}
        <button
          type="submit"
          disabled={busy || !file || !name.trim()}
          className="w-full rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50"
        >
          {busy ? "Creando..." : "Crear proyecto"}
        </button>
      </form>
    </div>
  )
}
