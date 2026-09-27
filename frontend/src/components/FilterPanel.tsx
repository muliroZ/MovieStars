import { useEffect, useRef, useState } from 'react'

import { useDebounce } from '../hooks/useDebounce'
import type { MovieStatus } from '../types/movie'
import {
  activeFilterCount,
  clearFilters,
  validateYearRange,
  type CatalogFilters,
  type GenreMode,
  type ReviewsFilter,
} from '../utils/catalogFilters'
import { MOVIE_STATUSES } from '../utils/movieForm'
import GenrePicker from './GenrePicker'
import StarInput from './StarInput'
import './FilterPanel.css'

/** Espera sem digitação antes de aplicar os anos (spec 100, D-8). */
const YEAR_DEBOUNCE_MS = 400

const GENRE_MODE_OPTIONS: { value: GenreMode; label: string }[] = [
  { value: 'any', label: 'Qualquer um' },
  { value: 'all', label: 'Todos' },
]

const REVIEWS_OPTIONS: { value: ReviewsFilter; label: string }[] = [
  { value: 'all', label: 'Todos' },
  { value: 'with', label: 'Com avaliação' },
  { value: 'without', label: 'Sem avaliação' },
]

interface FilterPanelProps {
  id: string
  hidden: boolean
  filters: CatalogFilters
  onChange: (filters: CatalogFilters) => void
}

/** Painel de filtros do catálogo (spec 100, CA-3 a CA-12). Cada mudança vale na hora. */
function FilterPanel({ id, hidden, filters, onChange }: FilterPanelProps) {
  function toggleStatus(status: MovieStatus) {
    const isSelected = filters.status.includes(status)
    // Mantém a ordem da lista de status.
    const next = MOVIE_STATUSES.filter((item) => (item === status ? !isSelected : filters.status.includes(item)))
    onChange({ ...filters, status: next })
  }

  function changeReviews(reviews: ReviewsFilter) {
    // "Sem avaliação" com mínimo de estrelas nunca teria resultado (CA-9).
    onChange({ ...filters, reviews, minStars: reviews === 'without' ? null : filters.minStars })
  }

  const withoutReviews = filters.reviews === 'without'

  return (
    <section id={id} className="filter-panel" aria-label="Filtros" hidden={hidden}>
      <div className="filter-panel__group">
        <GenrePicker selected={filters.genres} onChange={(genres) => onChange({ ...filters, genres })} />
        <fieldset className="filter-panel__fieldset" disabled={filters.genres.length === 0}>
          <legend className="filter-panel__sublegend">Combinar gêneros</legend>
          <div className="filter-panel__options">
            {GENRE_MODE_OPTIONS.map((option) => (
              <label key={option.value} className="filter-panel__radio">
                <input
                  type="radio"
                  name="filter-genre-mode"
                  checked={filters.genreMode === option.value}
                  onChange={() => onChange({ ...filters, genreMode: option.value })}
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>
      </div>

      <YearRange filters={filters} onChange={onChange} />

      <fieldset className="filter-panel__fieldset">
        <legend className="filter-panel__legend">Status</legend>
        <div className="filter-panel__options">
          {MOVIE_STATUSES.map((status) => (
            <label key={status} className="filter-panel__chip">
              <input type="checkbox" checked={filters.status.includes(status)} onChange={() => toggleStatus(status)} />
              <span>{status}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="filter-panel__fieldset">
        <legend className="filter-panel__legend">Avaliações</legend>
        <div className="filter-panel__options">
          {REVIEWS_OPTIONS.map((option) => (
            <label key={option.value} className="filter-panel__radio">
              <input
                type="radio"
                name="filter-reviews"
                checked={filters.reviews === option.value}
                onChange={() => changeReviews(option.value)}
              />
              {option.label}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="filter-panel__group">
        <span id="filter-min-stars-label" className="filter-panel__legend">
          Mínimo de estrelas
        </span>
        <div className="filter-panel__options">
          <StarInput
            value={filters.minStars}
            onChange={(stars) => onChange({ ...filters, minStars: stars })}
            firstInputId="filter-min-stars"
            labelId="filter-min-stars-label"
            disabled={withoutReviews}
          />
          <button
            type="button"
            className="filter-panel__button"
            disabled={withoutReviews || filters.minStars === null}
            onClick={() => onChange({ ...filters, minStars: null })}
          >
            Qualquer nota
          </button>
        </div>
      </div>

      <div className="filter-panel__footer">
        <button
          type="button"
          className="filter-panel__button"
          disabled={activeFilterCount(filters) === 0}
          onClick={() => onChange(clearFilters(filters))}
        >
          Limpar filtros
        </button>
      </div>
    </section>
  )
}

interface YearRangeProps {
  filters: CatalogFilters
  onChange: (filters: CatalogFilters) => void
}

/**
 * Campos "de" e "até" (CA-5, DEC-12). Têm estado próprio para aceitar digitação
 * incompleta; a URL só muda com valores válidos, depois da pausa.
 */
function YearRange({ filters, onChange }: YearRangeProps) {
  const [minInput, setMinInput] = useState(filters.yearMin?.toString() ?? '')
  const [maxInput, setMaxInput] = useState(filters.yearMax?.toString() ?? '')

  // Se a URL mudar por fora (voltar do navegador, "Limpar filtros"), os campos acompanham.
  const urlYears = `${filters.yearMin ?? ''}|${filters.yearMax ?? ''}`
  const [syncedYears, setSyncedYears] = useState(urlYears)
  if (urlYears !== syncedYears) {
    setSyncedYears(urlYears)
    setMinInput(filters.yearMin?.toString() ?? '')
    setMaxInput(filters.yearMax?.toString() ?? '')
  }

  // Os dois campos viram um texto só: um objeto novo a cada renderização reiniciaria a espera.
  const debouncedKey = useDebounce(JSON.stringify([minInput, maxInput]), YEAR_DEBOUNCE_MS)
  const [debouncedMin, debouncedMax] = JSON.parse(debouncedKey) as [string, string]
  // Os erros aparecem só depois da pausa, para não acusar um ano ainda sendo digitado.
  const errors = validateYearRange(debouncedMin, debouncedMax)
  const hasErrors = errors.yearMin !== undefined || errors.yearMax !== undefined

  const lastDebouncedKey = useRef(debouncedKey)
  useEffect(() => {
    // Só reage à digitação (após a pausa), não à sincronização vinda da URL.
    if (debouncedKey === lastDebouncedKey.current) return
    lastDebouncedKey.current = debouncedKey
    if (hasErrors) return // com erro, a lista não muda (CA-5)
    const yearMin = debouncedMin.trim() === '' ? null : Number(debouncedMin)
    const yearMax = debouncedMax.trim() === '' ? null : Number(debouncedMax)
    if (yearMin !== filters.yearMin || yearMax !== filters.yearMax) {
      onChange({ ...filters, yearMin, yearMax })
    }
  }, [debouncedKey, debouncedMin, debouncedMax, hasErrors, filters, onChange])

  return (
    <fieldset className="filter-panel__fieldset">
      <legend className="filter-panel__legend">Ano</legend>
      <div className="filter-panel__years">
        <YearField
          id="filter-year-min"
          label="De"
          value={minInput}
          onChange={setMinInput}
          error={errors.yearMin}
        />
        <YearField
          id="filter-year-max"
          label="Até"
          value={maxInput}
          onChange={setMaxInput}
          error={errors.yearMax}
        />
      </div>
    </fieldset>
  )
}

interface YearFieldProps {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  error?: string
}

function YearField({ id, label, value, onChange, error }: YearFieldProps) {
  return (
    <div className="filter-panel__year">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="text"
        inputMode="numeric"
        autoComplete="off"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
      />
      {error && (
        <p id={`${id}-error`} className="field-error">
          {error}
        </p>
      )}
    </div>
  )
}

export default FilterPanel
