import { Link, useLocation } from 'react-router-dom'

import type { MovieListItem } from '../types/movie'
import Poster from './Poster'
import StarRating from './StarRating'
import './MovieCard.css'

const MAX_GENRES = 3
const MAX_DIRECTORS = 2

interface MovieCardProps {
  movie: MovieListItem
}

function MovieCard({ movie }: MovieCardProps) {
  // A página de detalhes usa a busca atual para o "Voltar ao catálogo" (spec 002, CA-23).
  const { search: catalogSearch } = useLocation()

  return (
    <Link
      to={`/filmes/${movie.sk_movie_id}`}
      state={{ catalogSearch }}
      className="movie-card"
    >
      <Poster
        className="movie-card__poster"
        src={movie.url_poster}
        alt={`Pôster de ${movie.titulo}`}
      />
      <div className="movie-card__body">
        <h2 className="movie-card__title" title={movie.titulo}>
          {movie.titulo}
        </h2>
        <p className="movie-card__year">{movie.ano_lancamento ?? 'Ano não informado'}</p>
        <StarRating average={movie.media_estrelas} count={movie.qtd_avaliacoes} />
        <p className="movie-card__genres">{formatGenres(movie.generos)}</p>
        <p className="movie-card__directors">{formatDirectors(movie.diretores)}</p>
      </div>
    </Link>
  )
}

function formatGenres(genres: string[]): string {
  if (genres.length === 0) return 'Sem gênero'
  const shown = genres.slice(0, MAX_GENRES).join(', ')
  const hidden = genres.length - MAX_GENRES
  return hidden > 0 ? `${shown} +${hidden}` : shown
}

function formatDirectors(directors: string[]): string {
  if (directors.length === 0) return 'Diretor não informado'
  const shown = directors.slice(0, MAX_DIRECTORS).join(', ')
  const hidden = directors.length - MAX_DIRECTORS
  return `Direção: ${shown}${hidden > 0 ? ` e mais ${hidden}` : ''}`
}

export default MovieCard
