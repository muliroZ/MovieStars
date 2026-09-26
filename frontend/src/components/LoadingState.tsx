import './StatusState.css'

function LoadingState({ message = 'Carregando filmes…' }: { message?: string }) {
  return (
    <div className="status-state" role="status">
      <div className="status-state__spinner" aria-hidden="true" />
      <p className="status-state__message">{message}</p>
    </div>
  )
}

export default LoadingState
