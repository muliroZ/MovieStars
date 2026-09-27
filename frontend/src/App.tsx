import { Route, Routes } from 'react-router-dom'

import CatalogPage from './pages/CatalogPage'
import MovieDetailPage from './pages/MovieDetailPage'
import NotFoundPage from './pages/NotFoundPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<CatalogPage />} />
      <Route path="/filmes/:skMovieId" element={<MovieDetailPage />} />
      {/* Qualquer outro endereço. */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

export default App
