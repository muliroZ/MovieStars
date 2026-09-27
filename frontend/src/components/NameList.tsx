import { useState } from 'react'

import './NameList.css'

const VISIBLE_NAMES = 10

interface NameListProps {
  title: string
  names: string[]
}

/** Lista de nomes (equipe, elenco, produtoras): até 10, com "Mostrar todos" (CA-7 a CA-10). */
function NameList({ title, names }: NameListProps) {
  const [expanded, setExpanded] = useState(false)
  const visible = expanded ? names : names.slice(0, VISIBLE_NAMES)

  return (
    <section className="name-list">
      <h3 className="name-list__title">{title}</h3>
      {names.length === 0 ? (
        <p className="name-list__empty">Não informado</p>
      ) : (
        <>
          <ul className="name-list__items">
            {visible.map((name, index) => (
              <li key={`${name}-${index}`} className="name-list__item">
                {name}
              </li>
            ))}
          </ul>
          {names.length > VISIBLE_NAMES && (
            <button
              type="button"
              className="name-list__toggle"
              aria-expanded={expanded}
              onClick={() => setExpanded((value) => !value)}
            >
              {expanded ? 'Mostrar menos' : `Mostrar todos (${names.length})`}
            </button>
          )}
        </>
      )}
    </section>
  )
}

export default NameList
