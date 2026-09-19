import { NavLink, Outlet } from "react-router-dom"

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `block rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
    isActive ? "bg-violet-600 text-white" : "text-zinc-300 hover:bg-zinc-800 hover:text-white"
  }`

export function Layout() {
  return (
    <div className="flex min-h-screen bg-zinc-950 text-zinc-100">
      <aside className="w-56 shrink-0 border-r border-zinc-800 p-4">
        <div className="mb-6 px-2">
          <p className="text-lg font-semibold tracking-tight">Estudio IA</p>
          <p className="text-xs text-zinc-500">Fase 0 &middot; cimientos</p>
        </div>
        <nav className="space-y-1">
          <NavLink to="/" end className={linkClass}>
            Proyectos
          </NavLink>
          <NavLink to="/providers" className={linkClass}>
            Proveedores
          </NavLink>
        </nav>
      </aside>
      <main className="flex-1 overflow-y-auto p-8">
        <Outlet />
      </main>
    </div>
  )
}
