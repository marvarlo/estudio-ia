import { Route, HashRouter, Routes } from "react-router-dom"
import { Layout } from "./components/Layout"
import { ProjectsPage } from "./pages/ProjectsPage"
import { NewProjectPage } from "./pages/NewProjectPage"
import { ProjectDetailPage } from "./pages/ProjectDetailPage"
import { ChapterPage } from "./pages/ChapterPage"
import { ProvidersPage } from "./pages/ProvidersPage"

// HashRouter (no BrowserRouter): sirve como build estatico sin depender de
// configurar rewrites de servidor para rutas profundas -- se revisa cuando
// haya un servidor propio sirviendo el SPA en produccion.
function App() {
  return (
    <HashRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<ProjectsPage />} />
          <Route path="new" element={<NewProjectPage />} />
          <Route path="projects/:projectId" element={<ProjectDetailPage />} />
          <Route path="chapters/:chapterId" element={<ChapterPage />} />
          <Route path="providers" element={<ProvidersPage />} />
        </Route>
      </Routes>
    </HashRouter>
  )
}

export default App
