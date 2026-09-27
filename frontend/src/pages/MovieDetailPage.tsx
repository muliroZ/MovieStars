import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'

import { ApiError, errorMessage } from '../api/client'
import { deleteMovie } from '../api/movies'
import ConfirmDialog from '../components/ConfirmDialog'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import FinancialTable from '../components/FinancialTable'
import LoadingState from '../components/LoadingState'
import NameList from '../components/NameList'
import Poster from '../components/Poster'
import ReviewList from '../components/ReviewList'
import StarRating from '../components/StarRating'
import { useFlash } from '../hooks/useFlash'
import { useMovie } from '../hooks/useMovie'
import { type ReviewsResult, useMovieReviews } from '../hooks/useMovieReviews'
import type { MovieDetail } from '../types/movie'
import { formatDate, formatDuration } from '../utils/format'
import { catalogPath, catalogSearchFrom } from '../utils/navigation'
import './MovieDetailPage.css'

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
        <MovieContent
          key={movie.data.sk_movie_id}
          movie={movie.data}
          reviews={reviews}
          catalogState={location.state}
        />
      )}
    </div>
  )
}

interface MovieContentProps {
  movie: MovieDetail
  reviews: ReviewsResult
  /** Estado da navegação, repassado para editar e para voltar ao catálogo. */
  catalogState: unknown
}

function MovieContent({ movie, reviews, catalogState }: MovieContentProps) {
  const navigate = useNavigate()
  const { showFlash } = useFlash()
  const catalogSearch = catalogSearchFrom(catalogState)
  const [confirming, setConfirming] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  async function handleDelete() {
    setDeleting(true)
    setDeleteError(null)
    try {
      await deleteMovie(movie.sk_movie_id)
      showFlash('Filme excluído.')
      // Volta ao catálogo de onde veio (CA-27); replace: o filme não existe mais.
      navigate(catalogPath(catalogState), { replace: true })
    } catch (error) {
      setDeleting(false)
      setDeleteError(
        error instanceof ApiError && error.status === 404
          ? 'Filme não encontrado.'
          : errorMessage(error, 'Não foi possível excluir o filme.'),
      )
    }
  }

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
          <div className="movie-detail__actions">
            <Link
              to={`/filmes/${movie.sk_movie_id}/editar`}
              state={{ catalogSearch }}
              className="movie-detail__edit"
            >
              Editar
            </Link>
            <button
              type="button"
              className="movie-detail__delete"
              onClick={() => {
                setDeleteError(null)
                setConfirming(true)
              }}
            >
              Excluir
            </button>
          </div>
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

      <ConfirmDialog
        open={confirming}
        title={`Excluir "${movie.titulo.trim()}"?`}
        confirmLabel="Excluir definitivamente"
        busyLabel="Excluindo…"
        busy={deleting}
        error={deleteError}
        onConfirm={handleDelete}
        onCancel={() => setConfirming(false)}
      >
        {movie.qtd_avaliacoes > 0 && (
          <p>
            {movie.qtd_avaliacoes === 1
              ? 'A avaliação deste filme também será excluída.'
              : `As ${movie.qtd_avaliacoes.toLocaleString('pt-BR')} avaliações deste filme também serão excluídas.`}
          </p>
        )}
      </ConfirmDialog>
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
