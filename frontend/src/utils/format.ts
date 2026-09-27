/** Formatações de exibição em pt-BR, usadas por vários componentes. */

/**
 * Data do banco ("2017-02-01") → "01/02/2017".
 *
 * Divide o texto em vez de usar `new Date`: `new Date("2017-02-01")` é meia-noite
 * em UTC e, no fuso do Brasil (UTC−3), viraria 31/01/2017.
 */
export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split('-')
  return `${day}/${month}/${year}`
}

/** Data e hora em UTC ("2026-09-27T01:30:00Z") → data no fuso local ("26/09/2026"). */
export function formatDateTime(isoDateTime: string): string {
  return new Date(isoDateTime).toLocaleDateString('pt-BR')
}

/** Minutos → "1 h 42 min", "58 min" ou "2 h". Zero ou ausente → "Duração não informada". */
export function formatDuration(minutes: number | null): string {
  if (!minutes) return 'Duração não informada' // 0 significa desconhecida (spec 000, D-2)
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  if (hours === 0) return `${rest} min`
  return rest === 0 ? `${hours} h` : `${hours} h ${rest} min`
}

export type Currency = 'BRL' | 'USD'

const moneyFormatters: Record<Currency, Intl.NumberFormat> = {
  BRL: new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }),
  USD: new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'USD' }),
}

/** Valor em reais ou dólares no padrão brasileiro: "R$ 78.682.500,00", "US$ 25.000.000,00". */
export function formatMoney(value: number, currency: Currency): string {
  return moneyFormatters[currency].format(value)
}
