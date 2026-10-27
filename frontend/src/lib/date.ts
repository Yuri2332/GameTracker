export function timeZone() {
  return document.documentElement.dataset.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone
}

export function formatDate(value: string | Date, options: Intl.DateTimeFormatOptions = {}) {
  return new Intl.DateTimeFormat('pt-BR', { timeZone: timeZone(), ...options }).format(new Date(value))
}

export function formatDateTime(value: string | Date) {
  return formatDate(value, { dateStyle: 'short', timeStyle: 'short' })
}

export function formatTime(value: string | Date) {
  return formatDate(value, { hour: '2-digit', minute: '2-digit' })
}

export function localDateKey(value: string | Date) {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: timeZone(), year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date(value))
  const get = (name: string) => parts.find((part) => part.type === name)?.value || '00'
  return `${get('year')}-${get('month')}-${get('day')}`
}

export function localDateTimeInput(value?: string | Date | null) {
  const date = value ? new Date(value) : new Date()
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: timeZone(), year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(date)
  const get = (name: string) => parts.find((part) => part.type === name)?.value || '00'
  return `${get('year')}-${get('month')}-${get('day')}T${get('hour')}:${get('minute')}`
}

export function localDateTimeToIso(value: string) {
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/)
  if (!match) throw new Error('Informe uma data e hora válidas.')
  const [, year, month, day, hour, minute] = match.map(Number)
  const localAsUtc = Date.UTC(year, month - 1, day, hour, minute)
  let instant = localAsUtc
  for (let pass = 0; pass < 2; pass++) {
    const parts = new Intl.DateTimeFormat('en-CA', { timeZone: timeZone(), year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' }).formatToParts(new Date(instant))
    const get = (name: string) => Number(parts.find((part) => part.type === name)?.value || '0')
    const shownAsUtc = Date.UTC(get('year'), get('month') - 1, get('day'), get('hour'), get('minute'), get('second'))
    instant -= shownAsUtc - localAsUtc
  }
  return new Date(instant).toISOString()
}
