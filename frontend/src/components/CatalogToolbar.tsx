import { SORT_OPTIONS, type SortField } from '../utils/catalogFilters'
import './CatalogToolbar.css'

interface CatalogToolbarProps {
  panelId: string
  panelOpen: boolean
  onTogglePanel: () => void
  activeCount: number
  sort: SortField
  onSortChange: (sort: SortField) => void
  reverse: boolean
  onReverseChange: (reverse: boolean) => void
}

/** Barra acima da grade: abre os filtros, escolhe a ordenação e inverte a direção (spec 100, CA-1). */
function CatalogToolbar({
  panelId,
  panelOpen,
  onTogglePanel,
  activeCount,
  sort,
  onSortChange,
  reverse,
  onReverseChange,
}: CatalogToolbarProps) {
  return (
    <div className="catalog-toolbar">
      <button
        type="button"
        className="catalog-toolbar__button"
        aria-expanded={panelOpen}
        aria-controls={panelId}
        onClick={onTogglePanel}
      >
        {activeCount > 0 ? `Filtros (${activeCount})` : 'Filtros'}
      </button>

      <div className="catalog-toolbar__sort">
        <label htmlFor="catalog-sort">Ordenar por</label>
        <select
          id="catalog-sort"
          value={sort}
          onChange={(event) => onSortChange(event.target.value as SortField)}
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {/* aria-pressed faz o leitor de tela anunciar se a inversão está ligada (CA-1). */}
        <button
          type="button"
          className="catalog-toolbar__button"
          aria-pressed={reverse}
          onClick={() => onReverseChange(!reverse)}
        >
          Inverter
        </button>
      </div>
    </div>
  )
}

export default CatalogToolbar
