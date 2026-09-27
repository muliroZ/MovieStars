import { useEffect, useState } from 'react'

import { errorMessage } from '../api/client'
import { listGenres } from '../api/movies'
import './GenrePicker.css'

interface GenrePickerProps {
  selected: string[]
  onChange: (genres: string[]) => void
  error?: string
}

/** Seleção de gêneros entre os existentes (spec 003, CA-2 e CA-13). */
function GenrePicker({ selected, onChange, error }: GenrePickerProps) {
  const [attempt, setAttempt] = useState(0)
  const [result, setResult] = useState<{ attempt: number; genres: string[] | null; error: string | null } | null>(
    null,
  )

  useEffect(() => {
    const controller = new AbortController()
    listGenres(controller.signal)
      .then((genres) => setResult({ attempt, genres, error: null }))
      .catch((loadError: unknown) => {
        if (controller.signal.aborted) return
        setResult({ attempt, genres: null, error: errorMessage(loadError, 'Erro ao carregar os gêneros.') })
      })
    return () => controller.abort()
  }, [attempt])

  const current = result?.attempt === attempt ? result : null
  const options = current?.genres ?? []

  function toggle(name: string) {
    const isSelected = selected.includes(name)
    // Mantém a ordem alfabética da lista de opções.
    onChange(options.filter((genre) => (genre === name ? !isSelected : selected.includes(genre))))
  }

  return (
    <fieldset className="genre-picker" aria-describedby={error ? 'generos-error' : undefined}>
      <legend className="genre-picker__legend">Gêneros</legend>
      {current === null && <p className="genre-picker__status">Carregando gêneros…</p>}
      {current?.error && (
        <p className="genre-picker__status genre-picker__status--error">
          {current.error}{' '}
          <button type="button" className="genre-picker__retry" onClick={() => setAttempt((n) => n + 1)}>
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
