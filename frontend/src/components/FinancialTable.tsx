import type { MovieFinancials } from '../types/movie'
import { type Currency, formatMoney } from '../utils/format'
import './FinancialTable.css'

interface FinancialTableProps {
  /** null quando o filme não tem métricas cadastradas. */
  financials: MovieFinancials | null
}

interface Row {
  label: string
  brl: number | null
  usd: number | null
  isProfit: boolean
}

/** Orçamento, receita e lucro em real e dólar, como estão no banco (CA-11 a CA-14). */
function FinancialTable({ financials }: FinancialTableProps) {
  const rows: Row[] = [
    {
      label: 'Orçamento',
      brl: financials?.orcamento_brl ?? null,
      usd: financials?.orcamento_usd ?? null,
      isProfit: false,
    },
    {
      label: 'Receita',
      brl: financials?.receita_brl ?? null,
      usd: financials?.receita_usd ?? null,
      isProfit: false,
    },
    {
      label: 'Lucro',
      brl: financials?.lucro_brl ?? null,
      usd: financials?.lucro_usd ?? null,
      isProfit: true,
    },
  ]

  return (
    <table className="financial-table">
      <thead>
        <tr>
          <th scope="col">
            <span className="visually-hidden">Métrica</span>
          </th>
          <th scope="col">Real</th>
          <th scope="col">Dólar</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.label}>
            <th scope="row">{row.label}</th>
            <MoneyCell value={row.brl} currency="BRL" label="Real" isProfit={row.isProfit} />
            <MoneyCell value={row.usd} currency="USD" label="Dólar" isProfit={row.isProfit} />
          </tr>
        ))}
      </tbody>
    </table>
  )
}

interface MoneyCellProps {
  value: number | null
  currency: Currency
  label: string
  isProfit: boolean
}

function MoneyCell({ value, currency, label, isProfit }: MoneyCellProps) {
  if (value === null) {
    // Sem orçamento ou receita, o lucro não é calculado (spec 002, D-5).
    return (
      <td className="financial-table__missing" data-label={label}>
        {isProfit ? 'Não calculado' : 'Não informado'}
      </td>
    )
  }

  const isLoss = isProfit && value < 0
  return (
    <td className={isLoss ? 'financial-table__loss' : undefined} data-label={label}>
      {formatMoney(value, currency)}
      {isLoss && <span className="financial-table__tag">prejuízo</span>}
    </td>
  )
}

export default FinancialTable
