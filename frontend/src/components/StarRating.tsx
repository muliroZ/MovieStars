import './StarRating.css'

interface StarRatingProps {
  /** Média de 0 a 5 estrelas; null quando o filme não tem avaliações. */
  average: number | null
  /** Quantidade de avaliações; omitida numa avaliação individual. */
  count?: number
}

function StarRating({ average, count }: StarRatingProps) {
  if (average === null) {
    return <p className="star-rating star-rating--empty">Sem avaliações</p>
  }

  const value = average.toLocaleString('pt-BR', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })
  const countText =
    count === undefined
      ? null
      : `${count.toLocaleString('pt-BR')} ${count === 1 ? 'avaliação' : 'avaliações'}`
  const label = `${value} de 5 estrelas${countText ? `, ${countText}` : ''}`

  return (
    <p className="star-rating" aria-label={label}>
      <span className="star-rating__stars" aria-hidden="true">
        <span className="star-rating__base">★★★★★</span>
        <span className="star-rating__fill" style={{ width: `${(average / 5) * 100}%` }}>
          ★★★★★
        </span>
      </span>
      <span className="star-rating__value" aria-hidden="true">
        {value}
      </span>
      {countText && (
        <span className="star-rating__count" aria-hidden="true">
          ({countText})
        </span>
      )}
    </p>
  )
}

export default StarRating
