import { type FormEvent, useId, useRef, useState } from 'react'

import { ApiError, errorMessage } from '../api/client'
import { createReview } from '../api/movies'
import { useFlash } from '../hooks/useFlash'
import {
  EMPTY_REVIEW_FORM,
  REVIEW_COMMENT_MAX,
  REVIEW_NAME_MAX,
  type ReviewFormErrors,
  type ReviewFormField,
  type ReviewFormValues,
  reviewInputFromForm,
  validateReviewForm,
} from '../utils/reviewForm'
import StarInput from './StarInput'
import './ReviewForm.css'

const FIELD_ORDER: ReviewFormField[] = ['nome', 'estrelas', 'comentario']

interface ReviewFormProps {
  skMovieId: string
  /** Chamado depois de salvar, para atualizar a média e a lista (spec 004, CA-10 e CA-11). */
  onCreated: () => void
}

/** Formulário "Adicionar avaliação" (spec 004, CA-1 a CA-10, CA-14). */
function ReviewForm({ skMovieId, onCreated }: ReviewFormProps) {
  const ids = useId()
  const { showFlash } = useFlash()
  const [values, setValues] = useState(EMPTY_REVIEW_FORM)
  const [touched, setTouched] = useState<Set<ReviewFormField>>(new Set())
  const [serverErrors, setServerErrors] = useState<ReviewFormErrors>({})
  const [topError, setTopError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const submittingRef = useRef(false) // barra o duplo clique antes de a tela atualizar (CA-8)

  const fieldId = (field: ReviewFormField) => `${ids}-${field}`
  const clientErrors = validateReviewForm(values)

  function errorFor(field: ReviewFormField): string | undefined {
    return serverErrors[field] ?? (touched.has(field) ? clientErrors[field] : undefined)
  }

  function update<Field extends ReviewFormField>(field: Field, value: ReviewFormValues[Field]) {
    setValues((current) => ({ ...current, [field]: value }))
    setServerErrors((current) => ({ ...current, [field]: undefined }))
  }

  function touch(field: ReviewFormField) {
    setTouched((current) => new Set(current).add(field))
  }

  function focusFirst(errors: ReviewFormErrors) {
    const first = FIELD_ORDER.find((field) => errors[field])
    if (first) document.getElementById(fieldId(first))?.focus()
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (submittingRef.current) return

    const errors = validateReviewForm(values)
    if (Object.keys(errors).length > 0) {
      setTouched(new Set(FIELD_ORDER))
      focusFirst(errors)
      return
    }

    submittingRef.current = true
    setSubmitting(true)
    setTopError(null)
    try {
      await createReview(skMovieId, reviewInputFromForm(values))
      showFlash('Avaliação adicionada.')
      setValues(EMPTY_REVIEW_FORM) // nenhuma estrela marcada de novo (D-7)
      setTouched(new Set())
      onCreated()
    } catch (error) {
      if (error instanceof ApiError && error.status === 422) {
        setServerErrors(error.fieldErrors)
        setTopError(error.message) // "Alguns campos estão inválidos."
        focusFirst(error.fieldErrors)
      } else if (error instanceof ApiError && error.status === 404) {
        setTopError('Filme não encontrado.') // removido depois de a página abrir (CA-14)
      } else {
        // Falha de rede ou do servidor: o que foi digitado continua no formulário.
        setTopError(errorMessage(error, 'Não foi possível enviar a avaliação.'))
      }
    } finally {
      submittingRef.current = false
      setSubmitting(false)
    }
  }

  const nameError = errorFor('nome')
  const starsError = errorFor('estrelas')
  const commentError = errorFor('comentario')

  return (
    <form className="review-form" noValidate onSubmit={handleSubmit} aria-labelledby={`${ids}-title`}>
      <h3 id={`${ids}-title`} className="review-form__title">
        Adicionar avaliação
      </h3>
      {topError && (
        <p className="review-form__top-error" role="alert">
          {topError}
        </p>
      )}

      <div className="review-form__field">
        <label htmlFor={fieldId('nome')} className="review-form__label">
          Nome
        </label>
        <input
          id={fieldId('nome')}
          type="text"
          maxLength={REVIEW_NAME_MAX}
          autoComplete="name"
          value={values.nome}
          onChange={(event) => update('nome', event.target.value)}
          onBlur={() => touch('nome')}
          aria-invalid={nameError ? true : undefined}
          aria-describedby={nameError ? `${ids}-nome-error` : undefined}
        />
        {nameError && (
          <p id={`${ids}-nome-error`} className="field-error">
            {nameError}
          </p>
        )}
      </div>

      <div className="review-form__field">
        <span id={`${ids}-estrelas-label`} className="review-form__label">
          Nota
        </span>
        <StarInput
          value={values.estrelas}
          onChange={(stars) => update('estrelas', stars)}
          onBlur={() => touch('estrelas')}
          firstInputId={fieldId('estrelas')}
          labelId={`${ids}-estrelas-label`}
          describedBy={starsError ? `${ids}-estrelas-error` : undefined}
          invalid={Boolean(starsError)}
        />
        {starsError && (
          <p id={`${ids}-estrelas-error`} className="field-error">
            {starsError}
          </p>
        )}
      </div>

      <div className="review-form__field">
        <label htmlFor={fieldId('comentario')} className="review-form__label">
          Comentário
        </label>
        <textarea
          id={fieldId('comentario')}
          rows={4}
          maxLength={REVIEW_COMMENT_MAX}
          value={values.comentario}
          onChange={(event) => update('comentario', event.target.value)}
          onBlur={() => touch('comentario')}
          aria-invalid={commentError ? true : undefined}
          aria-describedby={`${ids}-contador${commentError ? ` ${ids}-comentario-error` : ''}`}
        />
        <div className="review-form__below">
          {commentError ? (
            <p id={`${ids}-comentario-error`} className="field-error">
              {commentError}
            </p>
          ) : (
            <span />
          )}
          <span id={`${ids}-contador`} className="review-form__counter">
            {values.comentario.length}/{REVIEW_COMMENT_MAX}
          </span>
        </div>
      </div>

      <button type="submit" className="review-form__submit" disabled={submitting}>
        {submitting ? 'Enviando…' : 'Enviar avaliação'}
      </button>
    </form>
  )
}

export default ReviewForm
