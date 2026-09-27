import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'

import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import FinancialTable from '../components/FinancialTable'
import LoadingState from '../components/LoadingState'
import NameList from '../components/NameList'
import Poster from '../components/Poster'
import ReviewList from '../components/ReviewList'
import StarRating from '../components/StarRating'
import { useMovie } from '../hooks/useMovie'
import { type ReviewsResult, useMovieReviews } from '../hooks/useMovieReviews'
import type { MovieDetail } from '../types/movie'
import { formatDate, formatDuration } from '../utils/format'
import './MovieDetailPage.css'

/** Endereço do catálogo de onde o usuário veio (estado passado pelo cartão), ou `/`. */
function catalogPath(state: unknown): string {
  if (
    typeof state === 'object' &&
    state !== null &&
    'catalogSearch' in state &&
    typeof state.catalogSearch === 'string'
  ) {
    return `/${state.catalogSearch}`
  }
  return '/' // endereço aberto direto: início do catálogo (CA-23)
}

function MovieDetailPage() {
  const { skMovieId = '' } = useParams()
  const location = useLocation()
  const backTo = catalogPath(location.state)
  const movie = useMovie(skMovieId)
  const reviews = useMovieReviews(skMovieId)

  // Ao abrir um filme, começa do topo (o roteador mantém a rolagem da tela anterior).
  useEffect(() => {
    window.scrollTo({ top: 0 })
  }, [skMovieId])

  // Título da aba (CA-25); volta ao padrão ao sair da página.
  const title = movie.status === 'success' ? movie.data.titulo.trim() : null
  useEffect(() => {
    document.title = title ? `${title} — MovieStars` : 'MovieStars'
    return () => {
      document.title = 'MovieStars'
    }
  }, [title])

  return (
    <div className="movie-detail">
      <header className="movie-detail__topbar">
        <Link to="/" className="movie-detail__brand">
          MovieStars
        </Link>
        <Link to={backTo} className="movie-detail__back">
          ← Voltar ao catálogo
        </Link>
      </header>

      {movie.status === 'loading' && <LoadingState message="Carregando filme…" />}
      {movie.status === 'error' && <ErrorState message={movie.message} onRetry={movie.retry} />}
      {movie.status === 'not-found' && (
        <EmptyState
          message="Filme não encontrado"
          action={<Link to="/">Ir para o catálogo</Link>}
        />
      )}
      {movie.status === 'success' && (
        // key: ao trocar de filme, listas expandidas etc. recomeçam do zero.
        <MovieContent key={movie.data.sk_movie_id} movie={movie.data} reviews={reviews} />
      )}
    </div>
  )
}

interface MovieContentProps {
  movie: MovieDetail
  reviews: ReviewsResult
}

function MovieContent({ movie, reviews }: MovieContentProps) {
  return (
    <main className="movie-detail__content">
      <Backdrop src={movie.url_backdrop} />

      <section className="movie-detail__hero">
        <Poster
          className="movie-detail__poster"
          src={movie.url_poster}
          alt={`Pôster de ${movie.titulo}`}
        />
        <div className="movie-detail__info">
          <h1 className="movie-detail__title">{movie.titulo}</h1>
          <StarRating average={movie.media_estrelas} count={movie.qtd_avaliacoes} />
          <dl className="movie-detail__facts">
            <dt>Ano</dt>
            <dd>{movie.ano_lancamento ?? 'Ano não informado'}</dd>
            <dt>Lançamento</dt>
            <dd>
              {movie.data_lancamento ? formatDate(movie.data_lancamento) : 'Data não informada'}
            </dd>
            <dt>Duração</dt>
            <dd>{formatDuration(movie.duracao_minutos)}</dd>
            <dt>Status</dt>
            <dd>{movie.status_filme ?? 'Status não informado'}</dd>
            <dt>Gêneros</dt>
            <dd>{movie.generos.length > 0 ? movie.generos.join(', ') : 'Sem gênero'}</dd>
          </dl>
          <p className="movie-detail__synopsis">{movie.sinopse ?? 'Sinopse não informada'}</p>
        </div>
      </section>

      <section className="movie-detail__section">
        <h2>Equipe e elenco</h2>
        <div className="movie-detail__columns">
          <NameList title="Direção" names={movie.diretores} />
          <NameList title="Roteiro" names={movie.roteiristas} />
          <NameList title="Elenco" names={movie.elenco} />
        </div>
      </section>

      <section className="movie-detail__section">
        <h2>Produção</h2>
        <NameList title="Produtoras" names={movie.produtoras} />
        {/* A tabela ocupa a largura toda: em meia coluna os valores longos não cabem. */}
        <div className="movie-detail__financials">
          <h3 className="movie-detail__subtitle">Dados financeiros</h3>
          <FinancialTable financials={movie.financeiro} />
        </div>
      </section>

      <div className="movie-detail__section">
        <ReviewList reviews={reviews} />
      </div>
    </main>
  )
}

/** Faixa com a imagem de fundo; some se não houver imagem ou se ela falhar (CA-6). */
function Backdrop({ src }: { src: string | null }) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null)
  if (src === null || src === failedSrc) return null

  return (
    <div className="movie-detail__backdrop">
      <img src={src} alt="" onError={() => setFailedSrc(src)} />
    </div>
  )
}

export default MovieDetailPage
