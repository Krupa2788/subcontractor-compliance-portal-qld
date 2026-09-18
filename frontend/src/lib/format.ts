/** ABNs are conventionally displayed as 11 digits grouped 2-3-3-3. */
export function formatAbn(abn: string) {
  return abn.replace(/^(\d{2})(\d{3})(\d{3})(\d{3})$/, '$1 $2 $3 $4')
}

export function formatDate(value: string | null) {
  if (!value) return '—'
  return new Date(value + 'T00:00:00').toLocaleDateString('en-AU', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

export function formatCurrency(value: number | null) {
  if (value == null) return '—'
  return new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: 'AUD',
    maximumFractionDigits: 0,
  }).format(value)
}
