import './StatusState.css'

interface ErrorStateProps {
  message: string
  onRetry: () => void
}

function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="status-state status-state--error" role="alert">
      <p className="status-state__message">{message}</p>
      <button type="button" className="status-state__button" onClick={onRetry}>
        Tentar novamente
      </button>
    </div>
  )
}

export default ErrorState
