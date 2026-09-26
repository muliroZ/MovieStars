import { useEffect, useState } from 'react'

/** Devolve `value` só depois de `delayMs` sem mudanças (ex.: pausa na digitação). */
export function useDebounce<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])

  return debounced
}
