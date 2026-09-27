import { Route, Routes } from 'react-router-dom'

import FlashProvider from './components/FlashProvider'
import CatalogPage from './pages/CatalogPage'
import MovieDetailPage from './pages/MovieDetailPage'
import MovieFormPage from './pages/MovieFormPage'
import NotFoundPage from './pages/NotFoundPage'

function App() {
  return (
    <FlashProvider>
      <Routes>
        <Route path="/" element={<CatalogPage />} />
        {/* O trecho fixo "novo" tem prioridade sobre :skMovieId. */}
        <Route path="/filmes/novo" element={<MovieFormPage />} />
        <Route path="/filmes/:skMovieId" element={<MovieDetailPage />} />
        <Route path="/filmes/:skMovieId/editar" element={<MovieFormPage />} />
        {/* Qualquer outro endereço. */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </FlashProvider>
  )
}

export default App
