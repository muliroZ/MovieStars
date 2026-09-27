import { type ReactNode, useCallback, useEffect, useMemo, useState } from 'react'

import { FlashContext } from '../hooks/useFlash'
import './FlashProvider.css'

const FLASH_DURATION_MS = 5000

/**
 * Guarda e mostra a mensagem de sucesso (spec 003, CA-31). Fica acima das rotas,
 * então a mensagem sobrevive à troca de página e não volta ao recarregar (DEC-9).
 */
function FlashProvider({ children }: { children: ReactNode }) {
  // id: a mesma mensagem mostrada duas vezes reinicia o tempo.
  const [flash, setFlash] = useState<{ id: number; message: string } | null>(null)

  const showFlash = useCallback((message: string) => {
    setFlash({ id: Date.now(), message })
  }, [])

  useEffect(() => {
    if (flash === null) return
    const timer = setTimeout(() => setFlash(null), FLASH_DURATION_MS)
    return () => clearTimeout(timer)
  }, [flash])

  const value = useMemo(() => ({ showFlash }), [showFlash])

  return (
    <FlashContext.Provider value={value}>
      {flash !== null && (
        <div className="flash" role="status">
          <p className="flash__message">{flash.message}</p>
          <button
            type="button"
            className="flash__close"
            aria-label="Fechar mensagem"
            onClick={() => setFlash(null)}
          >
            ×
          </button>
        </div>
      )}
      {children}
    </FlashContext.Provider>
  )
}

export default FlashProvider
