import { useState } from 'react'

const POSTER_PLACEHOLDER = '/poster-placeholder.svg'

interface PosterProps {
  src: string | null
  alt: string
  className?: string
}

/** Pôster do filme; sem imagem ou se ela falhar (URL quebrada, sem internet), mostra a padrão. */
function Poster({ src, alt, className }: PosterProps) {
  // Guarda qual URL falhou: se o componente passar a mostrar outro filme, a nova
  // imagem tem uma chance de carregar.
  const [failedSrc, setFailedSrc] = useState<string | null>(null)
  const showPlaceholder = src === null || src === failedSrc

  return (
    <img
      className={className}
      src={showPlaceholder ? POSTER_PLACEHOLDER : src}
      alt={alt}
      loading="lazy"
      onError={() => setFailedSrc(src)}
    />
  )
}

export default Poster
