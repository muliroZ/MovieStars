import { Link } from 'react-router-dom'

function NotFoundPage() {
  return (
    <main className="not-found">
      <h1>Página não encontrada</h1>
      <p>O endereço acessado não existe.</p>
      <Link to="/">Voltar ao catálogo</Link>
    </main>
  )
}

export default NotFoundPage
