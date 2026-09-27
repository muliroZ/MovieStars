import { createContext, useContext } from 'react'

export interface FlashContextValue {
  /** Mostra uma mensagem de sucesso no topo da tela (ex.: "Filme cadastrado."). */
  showFlash: (message: string) => void
}

export const FlashContext = createContext<FlashContextValue>({ showFlash: () => {} })

/** Acesso às mensagens de sucesso; o FlashProvider precisa envolver a aplicação. */
export function useFlash(): FlashContextValue {
  return useContext(FlashContext)
}
