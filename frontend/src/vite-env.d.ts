/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** URL base da API; padrão http://localhost:8000/api/v1 (constituição, seção 5.3). */
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
