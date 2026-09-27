import type { ReviewsResult } from '../hooks/useMovieReviews'
import { formatDateTime } from '../utils/format'
import ErrorState from './ErrorState'
import LoadingState from './LoadingState'
import StarRating from './StarRating'
import './ReviewList.css'

interface ReviewListProps {
  reviews: ReviewsResult
}

/** Avaliações do filme, 10 por vez, com "Mostrar mais" (CA-17 a CA-22). */
function ReviewList({ reviews }: ReviewListProps) {
  const title = reviews.status === 'success' ? `Avaliações (${reviews.total})` : 'Avaliações'

  return (
    <section className="review-list" aria-label="Avaliações">
      <h2 className="review-list__title">{title}</h2>

      {reviews.status === 'loading' && <LoadingState message="Carregando avaliações…" />}
      {reviews.status === 'error' && (
        <ErrorState message={reviews.message ?? ''} onRetry={reviews.retry} />
      )}
      {reviews.status === 'success' && reviews.total === 0 && (
        <p className="review-list__empty">Este filme ainda não tem avaliações.</p>
      )}

      {reviews.items.length > 0 && (
        <ul className="review-list__items">
          {reviews.items.map((review) => (
            <li key={review.sk_movie_review_id} className="review">
              <div className="review__header">
                <strong className="review__name">{review.nome}</strong>
                <time className="review__date" dateTime={review.created_at}>
                  {formatDateTime(review.created_at)}
                </time>
              </div>
              <StarRating average={review.estrelas} />
              <p className="review__comment">{review.comentario}</p>
            </li>
          ))}
        </ul>
      )}

      {reviews.loadMoreError !== null ? (
        <div className="review-list__more-error" role="alert">
          <p>{reviews.loadMoreError}</p>
          <button type="button" className="review-list__more" onClick={reviews.loadMore}>
            Tentar de novo
          </button>
        </div>
      ) : (
        reviews.hasMore && (
          <button
            type="button"
            className="review-list__more"
            onClick={reviews.loadMore}
            disabled={reviews.loadingMore}
          >
            {reviews.loadingMore ? 'Carregando…' : 'Mostrar mais avaliações'}
          </button>
        )
      )}
    </section>
  )
}

export default ReviewList
