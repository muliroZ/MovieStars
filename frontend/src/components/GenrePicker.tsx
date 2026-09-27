import { useGenres } from '../hooks/useGenres'
import './GenrePicker.css'

interface GenrePickerProps {
  selected: string[]
  onChange: (genres: string[]) => void
  error?: string
}

/** Seleção de gêneros entre os existentes (spec 003, CA-2 e CA-13). */
function GenrePicker({ selected, onChange, error }: GenrePickerProps) {
  const genres = useGenres()
  const options = genres.genres

  function toggle(name: string) {
    const isSelected = selected.includes(name)
    // Mantém a ordem alfabética da lista de opções.
    onChange(options.filter((genre) => (genre === name ? !isSelected : selected.includes(genre))))
  }

  return (
    <fieldset className="genre-picker" aria-describedby={error ? 'generos-error' : undefined}>
      <legend className="genre-picker__legend">Gêneros</legend>
      {genres.status === 'loading' && <p className="genre-picker__status">Carregando gêneros…</p>}
      {genres.status === 'error' && (
        <p className="genre-picker__status genre-picker__status--error">
          {genres.message}{' '}
          <button type="button" className="genre-picker__retry" onClick={genres.retry}>
            Tentar novamente
          </button>
        </p>
      )}
      {options.length > 0 && (
        <div className="genre-picker__options">
          {options.map((genre) => (
            <label key={genre} className="genre-picker__option">
              <input type="checkbox" checked={selected.includes(genre)} onChange={() => toggle(genre)} />
              <span>{genre}</span>
            </label>
          ))}
        </div>
      )}
      {error && (
        <p id="generos-error" className="field-error">
          {error}
        </p>
      )}
    </fieldset>
  )
}

export default GenrePicker
