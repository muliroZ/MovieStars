import { useId, useState } from 'react'

import './StarInput.css'

const STARS = [1, 2, 3, 4, 5]

interface StarInputProps {
  value: number | null
  onChange: (stars: number) => void
  onBlur?: () => void
  /** id do primeiro botão de opção, para o formulário focar em caso de erro. */
  firstInputId: string
  labelId: string
  describedBy?: string
  invalid?: boolean
  disabled?: boolean
}

/**
 * Nota de 1 a 5 estrelas inteiras (spec 004, CA-2). Cada estrela é um botão de opção
 * nativo escondido: setas do teclado, foco e leitores de tela já funcionam (DEC-7).
 */
function StarInput({
  value,
  onChange,
  onBlur,
  firstInputId,
  labelId,
  describedBy,
  invalid = false,
  disabled = false,
}: StarInputProps) {
  const groupName = useId()
  const [hovered, setHovered] = useState<number | null>(null)
  // Prévia ao passar o mouse; desabilitado, não há prévia (spec 100, CA-9).
  const highlighted = (disabled ? null : hovered) ?? value ?? 0

  return (
    <div
      role="radiogroup"
      aria-labelledby={labelId}
      aria-describedby={describedBy}
      aria-invalid={invalid || undefined}
      aria-disabled={disabled || undefined}
      className={`star-input${invalid ? ' star-input--invalid' : ''}${disabled ? ' star-input--disabled' : ''}`}
      onMouseLeave={() => setHovered(null)}
    >
      {STARS.map((stars) => (
        <label
          key={stars}
          className={`star-input__star${stars <= highlighted ? ' star-input__star--on' : ''}`}
          onMouseEnter={() => setHovered(stars)}
        >
          <input
            id={stars === 1 ? firstInputId : undefined}
            className="star-input__radio"
            type="radio"
            name={groupName}
            value={stars}
            checked={value === stars}
            onChange={() => onChange(stars)}
            onBlur={onBlur}
            disabled={disabled}
          />
          <span aria-hidden="true">★</span>
          <span className="visually-hidden">{stars} de 5 estrelas</span>
        </label>
      ))}
    </div>
  )
}

export default StarInput
