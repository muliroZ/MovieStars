// Provisório (T-14 a T-18): vitrine dos componentes com dados fixos.
// A tela real do catálogo substitui este arquivo na T-19.
import { useState } from 'react'

import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import LoadingState from '../components/LoadingState'
import MovieCard from '../components/MovieCard'
import Pagination from '../components/Pagination'
import SearchBar from '../components/SearchBar'
import type { MovieListItem } from '../types/movie'
import './CatalogPage.css'

const base: MovieListItem = {
  sk_movie_id: 'x',
  titulo: 'Rings',
  ano_lancamento: 2017,
  url_poster: 'https://image.tmdb.org/t/p/w500/yp4CDOVpVmNwiPoZKQeFCpW8CFo.jpg',
  media_estrelas: 3.8,
  qtd_avaliacoes: 12,
  generos: ['Horror'],
  diretores: ['F. Javier Gutiérrez'],
}

const samples: MovieListItem[] = [
  { ...base, sk_movie_id: '1' },
  {
    ...base,
    sk_movie_id: '2',
    titulo: 'Muitos gêneros e diretores',
    media_estrelas: 2.5,
    qtd_avaliacoes: 1,
    generos: ['Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Drama', 'Family', 'Fantasy', 'History', 'Horror', 'Music'],
    diretores: ['Ana Diretora', 'Beto Diretor', 'Caio Diretor'],
  },
  { ...base, sk_movie_id: '3', titulo: 'Sem pôster', url_poster: null, media_estrelas: 5, qtd_avaliacoes: 1234 },
  { ...base, sk_movie_id: '4', titulo: 'Pôster quebrado', url_poster: 'https://exemplo.invalido/p.jpg', media_estrelas: 0 },
  {
    ...base,
    sk_movie_id: '5',
    titulo: 'Um título muito longo '.repeat(7).trim().slice(0, 151),
    ano_lancamento: null,
    media_estrelas: null,
    qtd_avaliacoes: 0,
    generos: [],
    diretores: [],
  },
]

function CatalogPage() {
  const [search, setSearch] = useState('ring')

  return (
    <main style={{ padding: '1rem', display: 'grid', gap: '1.5rem' }}>
      <SearchBar value={search} onChange={setSearch} />
      <SearchBar value="" onChange={() => {}} />
      <ul className="movie-grid">
        {samples.map((movie) => (
          <li key={movie.sk_movie_id}>
            <MovieCard movie={movie} />
          </li>
        ))}
      </ul>
      <Pagination page={3} pages={4783} onChange={() => {}} />
      <Pagination page={1} pages={1} onChange={() => {}} />
      <LoadingState />
      <ErrorState message="Não foi possível carregar os filmes." onRetry={() => {}} />
      <EmptyState message='Nenhum filme encontrado para "xyz"' action={<button>Limpar busca</button>} />
    </main>
  )
}

export default CatalogPage
