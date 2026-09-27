import { type FormEvent, type ReactNode, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'

import { ApiError, errorMessage } from '../api/client'
import { createMovie, updateMovie } from '../api/movies'
import DirectorPicker from '../components/DirectorPicker'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import GenrePicker from '../components/GenrePicker'
import LoadingState from '../components/LoadingState'
import { useFlash } from '../hooks/useFlash'
import { useMovie } from '../hooks/useMovie'
import {
  EMPTY_MOVIE_FORM,
  MOVIE_STATUSES,
  type MovieFormErrors,
  type MovieFormField,
  type MovieFormValues,
  formFromMovie,
  maxYear,
  movieInputFromForm,
  validateMovieForm,
  yearOf,
} from '../utils/movieForm'
import { catalogPath, catalogSearchFrom } from '../utils/navigation'
import './MovieFormPage.css'

/** Ordem dos campos na tela: o foco vai para o primeiro com erro. */
const FIELD_ORDER: MovieFormField[] = [
  'titulo',
  'ano_lancamento',
  'status_filme',
  'data_lancamento',
  'duracao_minutos',
  'sinopse',
  'url_poster',
  'url_backdrop',
  'generos',
  'diretores',
]

/** Cadastro (`/filmes/novo`) ou edição (`/filmes/:skMovieId/editar`) de filme. */
function MovieFormPage() {
  const { skMovieId } = useParams()
  const location = useLocation()
  const backTo = catalogPath(location.state)

  return (
    <div className="movie-form-page">
      <header className="movie-form-page__topbar">
        <Link to="/" className="movie-form-page__brand">
          MovieStars
        </Link>
        <Link to={backTo} className="movie-form-page__back">
          ← Voltar ao catálogo
        </Link>
      </header>
      {skMovieId === undefined ? (
        <MovieForm title="Novo filme" initial={EMPTY_MOVIE_FORM} skMovieId={null} />
      ) : (
        <EditMovie skMovieId={skMovieId} />
      )}
    </div>
  )
}

/** Carrega o filme e abre o formulário preenchido (spec 003, CA-20, CA-25, CA-32). */
function EditMovie({ skMovieId }: { skMovieId: string }) {
  const movie = useMovie(skMovieId)

  if (movie.status === 'loading') return <LoadingState message="Carregando filme…" />
  if (movie.status === 'error') return <ErrorState message={movie.message} onRetry={movie.retry} />
  if (movie.status === 'not-found') {
    return <EmptyState message="Filme não encontrado" action={<Link to="/">Ir para o catálogo</Link>} />
  }
  return (
    <MovieForm
      key={movie.data.sk_movie_id}
      title="Editar filme"
      initial={formFromMovie(movie.data)}
      skMovieId={movie.data.sk_movie_id}
    />
  )
}

interface MovieFormProps {
  title: string
  initial: MovieFormValues
  /** null no cadastro; a chave do filme na edição. */
  skMovieId: string | null
}

function MovieForm({ title, initial, skMovieId }: MovieFormProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const { showFlash } = useFlash()
  const catalogSearch = catalogSearchFrom(location.state)

  const [values, setValues] = useState(initial)
  const [touched, setTouched] = useState<Set<MovieFormField>>(new Set())
  const [serverErrors, setServerErrors] = useState<MovieFormErrors>({})
  const [topError, setTopError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const submittingRef = useRef(false) // barra o duplo clique antes de a tela atualizar (CA-15)

  const clientErrors = validateMovieForm(values)

  function errorFor(field: MovieFormField): string | undefined {
    return serverErrors[field] ?? (touched.has(field) ? clientErrors[field] : undefined)
  }

  function update<Field extends MovieFormField>(field: Field, value: MovieFormValues[Field]) {
    setValues((current) => {
      const next = { ...current, [field]: value }
      // Escolher a data preenche o ano com o ano dela (CA-8).
      if (field === 'data_lancamento' && typeof value === 'string' && value !== '') {
        next.ano_lancamento = yearOf(value)
      }
      return next
    })
    setServerErrors((current) => ({ ...current, [field]: undefined }))
  }

  function touch(field: MovieFormField) {
    setTouched((current) => new Set(current).add(field))
  }

  function focusFirst(errors: MovieFormErrors) {
    const first = FIELD_ORDER.find((field) => errors[field])
    if (first) document.getElementById(`field-${first}`)?.focus()
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (submittingRef.current) return

    const errors = validateMovieForm(values)
    if (Object.keys(errors).length > 0) {
      setTouched(new Set(FIELD_ORDER))
      focusFirst(errors)
      return
    }

    submittingRef.current = true
    setSubmitting(true)
    setTopError(null)
    try {
      const input = movieInputFromForm(values)
      const saved = skMovieId === null ? await createMovie(input) : await updateMovie(skMovieId, input)
      showFlash(skMovieId === null ? 'Filme cadastrado.' : 'Filme atualizado.')
      // replace: o voltar do navegador não retorna ao formulário já enviado (DEC-13).
      navigate(`/filmes/${saved.sk_movie_id}`, { replace: true, state: { catalogSearch } })
    } catch (error) {
      submittingRef.current = false
      setSubmitting(false)
      if (error instanceof ApiError && error.status === 422) {
        setServerErrors(error.fieldErrors)
        setTopError(error.message) // "Alguns campos estão inválidos."
        focusFirst(error.fieldErrors)
      } else if (error instanceof ApiError && error.status === 404) {
        setTopError('Filme não encontrado.') // removido enquanto a edição estava aberta (CA-25)
      } else {
        // Falha de rede ou do servidor: o que foi digitado continua no formulário.
        setTopError(errorMessage(error, 'Não foi possível salvar o filme.'))
      }
    }
  }

  const cancelTo = skMovieId === null ? `/${catalogSearch}` : `/filmes/${skMovieId}`

  return (
    <main className="movie-form-page__content">
      <h1 className="movie-form-page__title">{title}</h1>
      <p className="movie-form-page__required">Campos com * são obrigatórios.</p>
      {topError && (
        <p className="movie-form-page__top-error" role="alert">
          {topError}
        </p>
      )}

      <form className="movie-form" noValidate onSubmit={handleSubmit}>
        <Field field="titulo" label="Título *" error={errorFor('titulo')} wide>
          <input
            id="field-titulo"
            type="text"
            maxLength={500}
            value={values.titulo}
            onChange={(event) => update('titulo', event.target.value)}
            onBlur={() => touch('titulo')}
            {...invalidProps('titulo', errorFor('titulo'))}
          />
        </Field>

        <Field field="ano_lancamento" label="Ano *" error={errorFor('ano_lancamento')}>
          <input
            id="field-ano_lancamento"
            type="text"
            inputMode="numeric"
            placeholder={`1888 a ${maxYear()}`}
            value={values.ano_lancamento}
            onChange={(event) => update('ano_lancamento', event.target.value)}
            onBlur={() => touch('ano_lancamento')}
            {...invalidProps('ano_lancamento', errorFor('ano_lancamento'))}
          />
        </Field>

        <Field field="status_filme" label="Status *" error={errorFor('status_filme')}>
          <select
            id="field-status_filme"
            value={values.status_filme}
            onChange={(event) => update('status_filme', event.target.value as MovieFormValues['status_filme'])}
            onBlur={() => touch('status_filme')}
            {...invalidProps('status_filme', errorFor('status_filme'))}
          >
            <option value="">Selecione</option>
            {MOVIE_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </Field>

        <Field field="data_lancamento" label="Data de lançamento" error={errorFor('data_lancamento')}>
          <input
            id="field-data_lancamento"
            type="date"
            value={values.data_lancamento}
            onChange={(event) => update('data_lancamento', event.target.value)}
            onBlur={() => {
              touch('data_lancamento')
              touch('ano_lancamento') // a data pode deixar o ano divergente
            }}
            {...invalidProps('data_lancamento', errorFor('data_lancamento'))}
          />
        </Field>

        <Field field="duracao_minutos" label="Duração (minutos)" error={errorFor('duracao_minutos')}>
          <input
            id="field-duracao_minutos"
            type="text"
            inputMode="numeric"
            placeholder="Vazio = não informada"
            value={values.duracao_minutos}
            onChange={(event) => update('duracao_minutos', event.target.value)}
            onBlur={() => touch('duracao_minutos')}
            {...invalidProps('duracao_minutos', errorFor('duracao_minutos'))}
          />
        </Field>

        <Field field="sinopse" label="Sinopse" error={errorFor('sinopse')} wide>
          <textarea
            id="field-sinopse"
            rows={5}
            maxLength={4000}
            value={values.sinopse}
            onChange={(event) => update('sinopse', event.target.value)}
            onBlur={() => touch('sinopse')}
            {...invalidProps('sinopse', errorFor('sinopse'))}
          />
        </Field>

        <Field field="url_poster" label="URL do pôster" error={errorFor('url_poster')}>
          <input
            id="field-url_poster"
            type="url"
            maxLength={2048}
            placeholder="https://"
            value={values.url_poster}
            onChange={(event) => update('url_poster', event.target.value)}
            onBlur={() => touch('url_poster')}
            {...invalidProps('url_poster', errorFor('url_poster'))}
          />
        </Field>

        <Field field="url_backdrop" label="URL da imagem de fundo" error={errorFor('url_backdrop')}>
          <input
            id="field-url_backdrop"
            type="url"
            maxLength={2048}
            placeholder="https://"
            value={values.url_backdrop}
            onChange={(event) => update('url_backdrop', event.target.value)}
            onBlur={() => touch('url_backdrop')}
            {...invalidProps('url_backdrop', errorFor('url_backdrop'))}
          />
        </Field>

        <div id="field-generos" className="movie-form__field movie-form__field--wide" tabIndex={-1}>
          <GenrePicker
            selected={values.generos}
            onChange={(genres) => update('generos', genres)}
            error={errorFor('generos')}
          />
        </div>

        <div id="field-diretores" className="movie-form__field movie-form__field--wide" tabIndex={-1}>
          <DirectorPicker
            selected={values.diretores}
            onChange={(directors) => update('diretores', directors)}
            error={errorFor('diretores')}
          />
        </div>

        <div className="movie-form__actions">
          <Link to={cancelTo} state={{ catalogSearch }} className="movie-form__cancel">
            Cancelar
          </Link>
          <button type="submit" className="movie-form__submit" disabled={submitting}>
            {submitting ? 'Salvando…' : 'Salvar'}
          </button>
        </div>
      </form>
    </main>
  )
}

/** Atributos de acessibilidade de um campo com ou sem erro. */
function invalidProps(field: MovieFormField, error: string | undefined) {
  return {
    'aria-invalid': error ? true : undefined,
    'aria-describedby': error ? `${field}-error` : undefined,
  }
}

interface FieldProps {
  field: MovieFormField
  label: string
  error: string | undefined
  wide?: boolean
  children: ReactNode
}

/** Rótulo, campo e mensagem de erro logo abaixo (CA-14). */
function Field({ field, label, error, wide = false, children }: FieldProps) {
  return (
    <div className={`movie-form__field${wide ? ' movie-form__field--wide' : ''}`}>
      <label htmlFor={`field-${field}`} className="movie-form__label">
        {label}
      </label>
      {children}
      {error && (
        <p id={`${field}-error`} className="field-error">
          {error}
        </p>
      )}
    </div>
  )
}

export default MovieFormPage
