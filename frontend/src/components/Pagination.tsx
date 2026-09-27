import './Pagination.css'

interface PaginationProps {
  page: number
  pages: number
  onChange: (page: number) => void
}

function Pagination({ page, pages, onChange }: PaginationProps) {
  const isFirst = page <= 1
  const isLast = page >= pages

  return (
    <nav className="pagination" aria-label="Paginação">
      <button
        type="button"
        className="pagination__button"
        onClick={() => onChange(1)}
        disabled={isFirst}
        aria-label="Primeira página"
      >
        « <span className="pagination__label">Primeira</span>
      </button>
      <button
        type="button"
        className="pagination__button"
        onClick={() => onChange(page - 1)}
        disabled={isFirst}
        aria-label="Página anterior"
      >
        ‹ <span className="pagination__label">Anterior</span>
      </button>
      <span className="pagination__status" aria-current="page">
        Página {page.toLocaleString('pt-BR')} de {pages.toLocaleString('pt-BR')}
      </span>
      <button
        type="button"
        className="pagination__button"
        onClick={() => onChange(page + 1)}
        disabled={isLast}
        aria-label="Próxima página"
      >
        <span className="pagination__label">Próxima</span> ›
      </button>
      <button
        type="button"
        className="pagination__button"
        onClick={() => onChange(pages)}
        disabled={isLast}
        aria-label="Última página"
      >
        <span className="pagination__label">Última</span> »
      </button>
    </nav>
  )
}

export default Pagination
