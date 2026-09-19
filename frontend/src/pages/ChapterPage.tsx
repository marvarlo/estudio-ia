import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { api, mediaUrl, type ChapterShots } from "../api/client"

export function ChapterPage() {
  const { chapterId } = useParams<{ chapterId: string }>()
  const [data, setData] = useState<ChapterShots | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!chapterId) return
    api
      .getChapterShots(chapterId)
      .then(setData)
      .catch((err) => setError(String(err.message ?? err)))
  }, [chapterId])

  if (error) return <p className="text-sm text-red-400">{error}</p>
  if (!data) return <p className="text-sm text-zinc-500">Cargando...</p>

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">
          Capitulo {data.chapter.numero}: {data.chapter.titulo}
        </h1>
        <p className="mt-1 text-sm text-zinc-400">{data.shots.length} shots</p>
      </div>

      <div className="space-y-3">
        {data.shots.map((shot) => {
          const imageUrl = mediaUrl(shot.image_asset_path)
          const audioUrl = mediaUrl(shot.audio_asset_path)
          return (
            <div key={shot.id} className="flex gap-4 rounded-xl border border-zinc-800 bg-zinc-900 p-4">
              <div className="flex h-28 w-48 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-zinc-800">
                {imageUrl ? (
                  <img src={imageUrl} alt={`Shot ${shot.orden}`} className="h-full w-full object-cover" />
                ) : (
                  <span className="text-xs text-zinc-600">sin imagen</span>
                )}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-500">
                  <span className="rounded bg-zinc-800 px-1.5 py-0.5 font-mono">#{shot.orden}</span>
                  <span
                    className={`rounded px-1.5 py-0.5 ${
                      shot.tipo === "Dialogo" ? "bg-amber-900 text-amber-200" : "bg-zinc-800"
                    }`}
                  >
                    {shot.tipo}
                  </span>
                  {shot.personaje_ids.length > 0 && <span>{shot.personaje_ids.join(", ")}</span>}
                  {shot.escenario_id && <span>&middot; {shot.escenario_id}</span>}
                  {shot.momento_dia && <span>&middot; {shot.momento_dia}</span>}
                  {shot.duracion_estimada_seg != null && <span>&middot; {shot.duracion_estimada_seg}s</span>}
                </div>
                <p className="mt-1 text-sm text-zinc-100">{shot.texto}</p>
                {shot.prompt_imagen && (
                  <p className="mt-1 truncate text-xs text-zinc-500" title={shot.prompt_imagen}>
                    {shot.prompt_imagen}
                  </p>
                )}
                {audioUrl && (
                  <audio controls src={audioUrl} className="mt-2 h-8 w-full max-w-sm">
                    <track kind="captions" />
                  </audio>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
