import { type KeyboardEvent, useEffect, useId, useState } from 'react'

import { searchDirectors } from '../api/movies'
import { useDebounce } from '../hooks/useDebounce'
import './DirectorPicker.css'

const MIN_SEARCH_LENGTH = 2
const MAX_NAME_LENGTH = 255

interface DirectorPickerProps {
  selected: string[]
  onChange: (directors: string[]) => void
  error?: string
}

/**
 * Diretores com sugestões (spec 003, CA-16 a CA-19). Escolher uma sugestão usa o
 * diretor existente; um nome digitado só reaproveita um existente se for idêntico,
 * senão vira um diretor novo ao salvar (marcado como "novo").
 */
function DirectorPicker({ selected, onChange, error }: DirectorPickerProps) {
  const listId = useId()
  const [text, setText] = useState('')
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)
  // Nomes que sabemos existir no banco: os que já vieram do filme e os vistos nas sugestões.
  const [known, setKnown] = useState<Set<string>>(() => new Set(selected))

  const term = useDebounce(text.trim(), 300)
  const [result, setResult] = useState<{ term: string; names: string[] } | null>(null)

  useEffect(() => {
    if (term.length < MIN_SEARCH_LENGTH) return
    const controller = new AbortController()
    searchDirectors(term, controller.signal)
      .then((names) => {
        setResult({ term, names })
        setKnown((current) => new Set([...current, ...names]))
      })
      .catch(() => {
        // Sem sugestões não impede adicionar o nome digitado.
      })
    return () => controller.abort()
  }, [term])

  const suggestions = result?.term === term && term.length >= MIN_SEARCH_LENGTH ? result.names : []
  const showList = open && text.trim().length >= MIN_SEARCH_LENGTH && suggestions.length > 0

  function add(rawName: string) {
    const name = rawName.trim()
    setText('')
    setOpen(false)
    setActiveIndex(-1)
    if (name === '' || name.length > MAX_NAME_LENGTH || selected.includes(name)) return
    onChange([...selected, name])
    if (!known.has(name) && name.length >= MIN_SEARCH_LENGTH) {
      // Adicionado antes das sugestões chegarem: confirma se o nome exato já existe.
      searchDirectors(name)
        .then((names) => {
          if (names.includes(name)) setKnown((current) => new Set([...current, name]))
        })
        .catch(() => {})
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown' && showList) {
      event.preventDefault()
      setActiveIndex((index) => (index + 1) % suggestions.length)
    } else if (event.key === 'ArrowUp' && showList) {
      event.preventDefault()
      setActiveIndex((index) => (index <= 0 ? suggestions.length - 1 : index - 1))
    } else if (event.key === 'Enter') {
      event.preventDefault() // não envia o formulário
      add(showList && activeIndex >= 0 ? suggestions[activeIndex] : text)
    } else if (event.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div className="director-picker">
      <label htmlFor={`${listId}-input`} className="director-picker__label">
        Diretores
      </label>
      {selected.length > 0 && (
        <ul className="director-picker__chips" aria-label="Diretores adicionados">
          {selected.map((name) => (
            <li key={name} className="director-picker__chip">
              <span>{name}</span>
              {!known.has(name) && <span className="director-picker__new">novo</span>}
              <button
                type="button"
                className="director-picker__remove"
                aria-label={`Remover ${name}`}
                onClick={() => onChange(selected.filter((item) => item !== name))}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="director-picker__field">
        <input
          id={`${listId}-input`}
          className="director-picker__input"
          type="text"
          role="combobox"
          aria-expanded={showList}
          aria-controls={`${listId}-list`}
          aria-autocomplete="list"
          aria-activedescendant={showList && activeIndex >= 0 ? `${listId}-option-${activeIndex}` : undefined}
          aria-describedby={`${listId}-hint${error ? ' diretores-error' : ''}`}
          autoComplete="off"
          maxLength={MAX_NAME_LENGTH}
          placeholder="Digite um nome"
          value={text}
          onChange={(event) => {
            setText(event.target.value)
            setOpen(true)
            setActiveIndex(-1)
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onKeyDown={handleKeyDown}
        />
        <button
          type="button"
          className="director-picker__add"
          disabled={text.trim() === ''}
          onClick={() => add(text)}
        >
          Adicionar
        </button>
        {showList && (
          <ul id={`${listId}-list`} className="director-picker__list" role="listbox">
            {suggestions.map((name, index) => (
              <li
                key={name}
                id={`${listId}-option-${index}`}
                role="option"
                aria-selected={index === activeIndex}
                className="director-picker__option"
                // mousedown: escolhe antes de o campo perder o foco e fechar a lista
                onMouseDown={(event) => {
                  event.preventDefault()
                  add(name)
                }}
              >
                {name}
              </li>
            ))}
          </ul>
        )}
      </div>
      <p id={`${listId}-hint`} className="director-picker__hint">
        Digite ao menos 2 letras para ver sugestões. Enter ou "Adicionar" inclui o nome digitado.
      </p>
      {error && (
        <p id="diretores-error" className="field-error">
          {error}
        </p>
      )}
    </div>
  )
}

export default DirectorPicker
