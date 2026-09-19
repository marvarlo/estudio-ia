import { useEffect, useState } from "react"
import { api, type Provider, type ProviderHealth } from "../api/client"

export function ProvidersPage() {
  const [providers, setProviders] = useState<Provider[]>([])
  const [results, setResults] = useState<Record<string, ProviderHealth | "loading">>({})
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.listProviders().then(setProviders).catch((err) => setError(String(err.message ?? err)))
  }, [])

  async function handleTest(providerId: string) {
    setResults((prev) => ({ ...prev, [providerId]: "loading" }))
    try {
      const health = await api.testProvider(providerId)
      setResults((prev) => ({ ...prev, [providerId]: health }))
    } catch (err) {
      setResults((prev) => ({
        ...prev,
        [providerId]: { ok: false, detail: String((err as Error).message ?? err), latency_ms: null },
      }))
    }
  }

  if (error) return <p className="text-sm text-red-400">{error}</p>

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Proveedores de IA</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Registro de adaptadores disponibles (seccion 9 del doc de arquitectura). "Probar" ejecuta la prueba de humo
          real de cada uno.
        </p>
      </div>

      <div className="space-y-3">
        {providers.map((provider) => {
          const result = results[provider.id]
          return (
            <div key={provider.id} className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-zinc-100">{provider.name}</p>
                  <p className="text-xs text-zinc-500">
                    {provider.kind === "local" ? "Local" : "Nube"} &middot; {provider.capabilities.join(", ")}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${
                      provider.configured ? "bg-emerald-900 text-emerald-200" : "bg-zinc-700 text-zinc-300"
                    }`}
                  >
                    {provider.configured ? "Configurado" : "Sin configurar"}
                  </span>
                  <button
                    onClick={() => handleTest(provider.id)}
                    disabled={result === "loading"}
                    className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-500 disabled:opacity-50"
                  >
                    {result === "loading" ? "Probando..." : "Probar"}
                  </button>
                </div>
              </div>
              {result && result !== "loading" && (
                <p className={`mt-2 text-xs ${result.ok ? "text-emerald-300" : "text-red-300"}`}>
                  {result.detail}
                  {result.latency_ms != null && ` (${result.latency_ms.toFixed(0)} ms)`}
                </p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
