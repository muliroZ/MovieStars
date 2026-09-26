import './SearchBar.css'

/** Mesmo limite da API (CA-26). */
export const MAX_SEARCH_LENGTH = 200

interface SearchBarProps {
  value: string
  onChange: (value: string) => void
}

function SearchBar({ value, onChange }: SearchBarProps) {
  return (
    <div className="search-bar" role="search">
      <label htmlFor="search-input" className="visually-hidden">
        Buscar filmes pelo título
      </label>
      <input
        id="search-input"
        className="search-bar__input"
        type="search"
        placeholder="Buscar pelo título…"
        autoComplete="off"
        maxLength={MAX_SEARCH_LENGTH}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      {value !== '' && (
        <button type="button" className="search-bar__clear" onClick={() => onChange('')}>
          Limpar
        </button>
      )}
    </div>
  )
}

export default SearchBar
