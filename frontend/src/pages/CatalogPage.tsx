import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import CatalogToolbar from '../components/CatalogToolbar'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import FilterPanel from '../components/FilterPanel'
import LoadingState from '../components/LoadingState'
import MovieCard from '../components/MovieCard'
import Pagination from '../components/Pagination'
import SearchBar from '../components/SearchBar'
import { useDebounce } from '../hooks/useDebounce'
import { useGenres } from '../hooks/useGenres'
import { useMovies } from '../hooks/useMovies'
import type { MovieListItem, Page } from '../types/movie'
import {
  activeFilterCount,
  clearFilters,
  parseFilters,
  writeFilters,
  type CatalogFilters,
} from '../utils/catalogFilters'
import './CatalogPage.css'

const SEARCH_DEBOUNCE_MS = 300
const FILTER_PANEL_ID = 'catalog-filters'

/** Página vinda da URL; qualquer valor que não seja inteiro ≥ 1 vale 1 (CA-20). */
function parsePage(raw: string | null): number {
  if (raw === null || !/^\d+$/.test(raw)) return 1
  const page = Number(raw)
  return Number.isSafeInteger(page) && page >= 1 ? page : 1
}

/**
 * Parâmetros da URL sem os valores padrão: `/` é a página 1 sem busca nem filtros
 * (spec 001, CA-18; spec 100, CA-19).
 */
function buildParams(page: number, search: string, filters: CatalogFilters): URLSearchParams {
  const params = new URLSearchParams()
  if (search !== '') params.set('search', search)
  writeFilters(params, filters)
  if (page > 1) params.set('page', String(page))
  return params
}

function CatalogPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const page = parsePage(searchParams.get('page'))
  const search = (searchParams.get('search') ?? '').trim()
  // useMemo mantém o mesmo objeto enquanto a URL não muda (evita efeitos repetidos no painel).
  const filters = useMemo(() => parseFilters(searchParams), [searchParams])
  const movies = useMovies(page, search, filters)
  const genres = useGenres()
  const [panelOpen, setPanelOpen] = useState(false) // não vai para a URL (spec 100, D-12)

  // O campo tem estado próprio (atualiza a cada tecla); a URL só muda após a pausa.
  const [searchInput, setSearchInput] = useState(search)
  // Se a URL mudar por fora (voltar/avançar do navegador), o campo acompanha.
  const [syncedSearch, setSyncedSearch] = useState(search)
  if (search !== syncedSearch) {
    setSyncedSearch(search)
    setSearchInput(search)
  }

  const debouncedInput = useDebounce(searchInput, SEARCH_DEBOUNCE_MS)
  const lastDebounced = useRef(debouncedInput)
  useEffect(() => {
    // Só reage quando o texto digitado (após a pausa) muda, e não quando a URL muda
    // pelo voltar do navegador; senão o voltar seria desfeito.
    if (debouncedInput === lastDebounced.current) return
    lastDebounced.current = debouncedInput
    const term = debouncedInput.trim()
    if (term !== search) {
      setSearchParams(buildParams(1, term, filters)) // nova busca volta para a página 1 (CA-16)
    }
  }, [debouncedInput, search, filters, setSearchParams])

  // Gêneros que não existem saem da URL, sem criar entrada no histórico (spec 100, CA-20).
  useEffect(() => {
    if (genres.status !== 'success') return
    const valid = filters.genres.filter((genre) => genres.genres.includes(genre))
    if (valid.length !== filters.genres.length) {
      setSearchParams(buildParams(page, search, { ...filters, genres: valid }), { replace: true })
    }
  }, [genres.status, genres.genres, filters, page, search, setSearchParams])

  // Troca de página (inclusive pelo voltar do navegador): volta ao topo (CA-5).
  useEffect(() => {
    window.scrollTo({ top: 0 })
  }, [page])

  function handleSearchChange(value: string) {
    setSearchInput(value)
    if (value === '') setSearchParams(buildParams(1, '', filters)) // limpar não espera a pausa
  }

  function goToPage(target: number) {
    setSearchParams(buildParams(target, search, filters))
  }

  // Cada mudança de filtro ou ordenação cria uma entrada no histórico e volta à página 1 (CA-11).
  function setFilters(next: CatalogFilters) {
    setSearchParams(buildParams(1, search, next))
  }

  return (
    <div className="catalog">
      <header className="catalog__header">
        <Link to="/" className="catalog__brand">
          MovieStars
        </Link>
        <SearchBar value={searchInput} onChange={handleSearchChange} />
        <Link to="/filmes/novo" state={{ catalogSearch: searchParams.size ? `?${searchParams}` : '' }} className="catalog__new">
          Novo filme
        </Link>
      </header>

      <main className="catalog__content">
        <CatalogToolbar
          panelId={FILTER_PANEL_ID}
          panelOpen={panelOpen}
          onTogglePanel={() => setPanelOpen((open) => !open)}
          activeCount={activeFilterCount(filters)}
          sort={filters.sort}
          onSortChange={(sort) => setFilters({ ...filters, sort })}
          reverse={filters.reverse}
          onReverseChange={(reverse) => setFilters({ ...filters, reverse })}
        />
        <FilterPanel id={FILTER_PANEL_ID} hidden={!panelOpen} filters={filters} onChange={setFilters} />

        {movies.status === 'loading' && <LoadingState />}
        {movies.status === 'error' && (
          <ErrorState message={movies.message} onRetry={movies.retry} />
        )}
        {movies.status === 'success' && (
          <CatalogResults
            data={movies.data}
            search={search}
            filters={filters}
            onClearSearch={() => handleSearchChange('')}
            onClearFilters={() => setFilters(clearFilters(filters))}
            onPageChange={goToPage}
          />
        )}
      </main>
    </div>
  )
}

interface CatalogResultsProps {
  data: Page<MovieListItem>
  search: string
  filters: CatalogFilters
  onClearSearch: () => void
  onClearFilters: () => void
  onPageChange: (page: number) => void
}

function CatalogResults({
  data,
  search,
  filters,
  onClearSearch,
  onClearFilters,
  onPageChange,
}: CatalogResultsProps) {
  const activeCount = activeFilterCount(filters)

  if (data.total === 0 && activeCount > 0) {
    return (
      <EmptyState
        message="Nenhum filme encontrado com os filtros escolhidos."
        action={
          <button type="button" className="status-state__button" onClick={onClearFilters}>
            Limpar filtros
          </button>
        }
      />
    )
  }

  if (data.total === 0 && search === '') {
    return <EmptyState message="Nenhum filme cadastrado" />
  }

  if (data.total === 0) {
    return (
      <EmptyState
        message={`Nenhum filme encontrado para "${search}"`}
        action={
          <button type="button" className="status-state__button" onClick={onClearSearch}>
            Limpar busca
          </button>
        }
      />
    )
  }

  if (data.items.length === 0) {
    return (
      <EmptyState
        message="Esta página não existe"
        action={<Link to={`/?${buildParams(1, search, filters)}`}>Ir para a página 1</Link>}
      />
    )
  }

  const total = data.total.toLocaleString('pt-BR')
  const found =
    search === ''
      ? `${total} ${data.total === 1 ? 'filme' : 'filmes'}`
      : `${total} ${data.total === 1 ? 'filme encontrado' : 'filmes encontrados'} para "${search}"`
  // " · K filtros ativos" só quando há filtro (spec 100, CA-17).
  const summary =
    activeCount === 0
      ? found
      : `${found} · ${activeCount} ${activeCount === 1 ? 'filtro ativo' : 'filtros ativos'}`

  return (
    <>
      <p className="catalog__summary" aria-live="polite">
        {summary}
      </p>
      <ul className="movie-grid">
        {data.items.map((movie) => (
          <li key={movie.sk_movie_id}>
            <MovieCard movie={movie} />
          </li>
        ))}
      </ul>
      <Pagination page={data.page} pages={data.pages} onChange={onPageChange} />
    </>
  )
}

export default CatalogPage
