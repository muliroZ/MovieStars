/**
 * Formulário de nova avaliação: valores, validação e conversão para a API.
 *
 * Regras e mensagens repetem as do backend (`ReviewInput`), como `movieForm.ts`
 * faz para filmes (spec 004, CA-4 a CA-7). Mudou uma, mude a outra.
 */

import type { ReviewInput } from '../types/movie'

export const REVIEW_NAME_MAX = 120
export const REVIEW_COMMENT_MAX = 1000

export interface ReviewFormValues {
  nome: string
  /** null enquanto nenhuma estrela foi escolhida (spec 004, D-7). */
  estrelas: number | null
  comentario: string
}

export type ReviewFormField = keyof ReviewFormValues
export type ReviewFormErrors = Partial<Record<ReviewFormField, string>>

export const EMPTY_REVIEW_FORM: ReviewFormValues = { nome: '', estrelas: null, comentario: '' }

export function validateReviewForm(values: ReviewFormValues): ReviewFormErrors {
  const errors: ReviewFormErrors = {}

  const name = values.nome.trim()
  if (name === '') errors.nome = 'Campo obrigatório.'
  else if (name.length > REVIEW_NAME_MAX) errors.nome = `Deve ter no máximo ${REVIEW_NAME_MAX} caracteres.`

  if (values.estrelas === null) errors.estrelas = 'Campo obrigatório.'
  else if (!Number.isInteger(values.estrelas)) errors.estrelas = 'Deve ser um número inteiro.'
  else if (values.estrelas < 1) errors.estrelas = 'Deve ser no mínimo 1.'
  else if (values.estrelas > 5) errors.estrelas = 'Deve ser no máximo 5.'

  const comment = values.comentario.trim()
  if (comment === '') errors.comentario = 'Campo obrigatório.'
  else if (comment.length > REVIEW_COMMENT_MAX) {
    errors.comentario = `Deve ter no máximo ${REVIEW_COMMENT_MAX} caracteres.`
  }

  return errors
}

/** Converte valores já validados no corpo do POST. */
export function reviewInputFromForm(values: ReviewFormValues): ReviewInput {
  return {
    nome: values.nome.trim(),
    estrelas: values.estrelas as number, // validado antes
    comentario: values.comentario.trim(),
  }
}
