/** Cliente HTTP: único lugar do frontend que usa `fetch` (constituição, seção 5.3). */

export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

/** Erro com mensagem pronta para mostrar ao usuário. */
export class ApiError extends Error {
  readonly status: number | null

  constructor(message: string, status: number | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type QueryParams = Record<string, string | number | undefined>

export async function apiGet<T>(
  path: string,
  params: QueryParams = {},
  signal?: AbortSignal,
): Promise<T> {
  const url = new URL(`${API_URL}${path}`)
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') {
      url.searchParams.set(key, String(value))
    }
  }

  let response: Response
  try {
    response = await fetch(url, { signal })
  } catch (error) {
    // Requisição cancelada de propósito (ex.: o usuário mudou de página): repassa.
    if (signal?.aborted) throw error
    throw new ApiError('Não foi possível conectar ao servidor. Verifique se a API está rodando.')
  }

  if (!response.ok) {
    throw new ApiError(`O servidor respondeu com erro (${response.status}).`, response.status)
  }
  return (await response.json()) as T
}

/** Mensagem para mostrar ao usuário a partir de um erro qualquer. */
export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}
