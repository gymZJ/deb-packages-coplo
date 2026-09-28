export function formatSize(bytes) {
  if (!Number.isFinite(bytes)) return '—'
  const mib = bytes / 1024 / 1024
  return mib >= 10 ? `${mib.toFixed(1)} MB` : `${mib.toFixed(2)} MB`
}

export function formatDate(value, locale = 'en') {
  if (!value) return '—'
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(value))
}
