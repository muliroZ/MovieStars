import type { ReactNode } from 'react'

import './StatusState.css'

interface EmptyStateProps {
  message: string
  /** Botão ou link opcional (ex.: "Limpar busca"). */
  action?: ReactNode
}

function EmptyState({ message, action }: EmptyStateProps) {
  return (
    <div className="status-state">
      <p className="status-state__message">{message}</p>
      {action}
    </div>
  )
}

export default EmptyState
