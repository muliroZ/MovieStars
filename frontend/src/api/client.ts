/** Cliente HTTP: único lugar do frontend que usa `fetch` (constituição, seção 5.3). */

export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

/** Erro com mensagem pronta para mostrar ao usuário. */
export class ApiError extends Error {
  readonly status: number | null
  /** Erros de validação (422) por campo: nome do campo da API → mensagem. */
  readonly fieldErrors: Record<string, string>

  constructor(message: string, status: number | null = null, fieldErrors: Record<string, string> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fieldErrors = fieldErrors
  }
}

/** Parâmetros da URL; listas repetem a chave (`genre=Drama&genre=Horror`). */
export type QueryParams = Record<string, string | number | boolean | string[] | undefined>

interface RequestOptions {
  params?: QueryParams
  body?: unknown
  signal?: AbortSignal
}

async function request<T>(method: string, path: string, options: RequestOptions): Promise<T> {
  const url = new URL(`${API_URL}${path}`)
  for (const [key, value] of Object.entries(options.params ?? {})) {
    if (Array.isArray(value)) {
      for (const item of value) url.searchParams.append(key, item)
    } else if (value !== undefined && value !== '') {
      url.searchParams.set(key, String(value))
    }
  }

  const hasBody = options.body !== undefined
  let response: Response
  try {
    response = await fetch(url, {
      method,
      signal: options.signal,
      headers: hasBody ? { 'Content-Type': 'application/json' } : undefined,
      body: hasBody ? JSON.stringify(options.body) : undefined,
    })
  } catch (error) {
    // Requisição cancelada de propósito (ex.: o usuário mudou de página): repassa.
    if (options.signal?.aborted) throw error
    throw new ApiError('Não foi possível conectar ao servidor. Verifique se a API está rodando.')
  }

  if (!response.ok) {
    throw await errorFromResponse(response)
  }
  if (response.status === 204) {
    return undefined as T // sem corpo (ex.: exclusão)
  }
  return (await response.json()) as T
}

/** Monta o ApiError a partir do corpo da resposta de erro da API. */
async function errorFromResponse(response: Response): Promise<ApiError> {
  let body: unknown = null
  try {
    body = await response.json()
  } catch {
    // resposta de erro sem corpo JSON
  }
  const detail = typeof body === 'object' && body !== null && 'detail' in body ? body.detail : null

  if (typeof detail === 'string') {
    return new ApiError(detail, response.status) // ex.: "Filme não encontrado."
  }
  if (Array.isArray(detail)) {
    // 422: [{ loc: ["body", "titulo"], msg: "Campo obrigatório." }, ...]
    const fieldErrors: Record<string, string> = {}
    for (const item of detail) {
      if (isValidationItem(item)) {
        const field = String(item.loc[1] ?? item.loc[0])
        fieldErrors[field] ??= item.msg
      }
    }
    return new ApiError('Alguns campos estão inválidos.', response.status, fieldErrors)
  }
  return new ApiError(`O servidor respondeu com erro (${response.status}).`, response.status)
}

function isValidationItem(item: unknown): item is { loc: (string | number)[]; msg: string } {
  return (
    typeof item === 'object' &&
    item !== null &&
    'loc' in item &&
    Array.isArray(item.loc) &&
    'msg' in item &&
    typeof item.msg === 'string'
  )
}

export function apiGet<T>(path: string, params: QueryParams = {}, signal?: AbortSignal): Promise<T> {
  return request<T>('GET', path, { params, signal })
}

/** POST, PUT ou DELETE com corpo JSON opcional. */
export function apiSend<T>(method: 'POST' | 'PUT' | 'DELETE', path: string, body?: unknown): Promise<T> {
  return request<T>(method, path, { body })
}

/** Mensagem para mostrar ao usuário a partir de um erro qualquer. */
export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}
