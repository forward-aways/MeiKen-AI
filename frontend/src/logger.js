/**
 * Lightweight frontend logger.
 *
 * Console output with a timestamp prefix in all environments; global handlers
 * capture uncaught errors and unhandled promise rejections so failures are
 * never silent. A remote report hook can be added later if needed.
 */

const PREFIX = '[MeiKen]'

function ts() {
  const d = new Date()
  return d.toTimeString().slice(0, 8)
}

export const log = {
  info: (...args) => console.log(`%c${ts()} ${PREFIX}`, 'color:#7c79f7', ...args),
  warn: (...args) => console.warn(`${ts()} ${PREFIX}`, ...args),
  error: (...args) => console.error(`${ts()} ${PREFIX}`, ...args),
}

let installed = false

export function installGlobalHandlers() {
  if (installed) return
  installed = true
  window.addEventListener('error', (e) => {
    log.error('window.onerror |', e.message, `${e.filename || ''}:${e.lineno || 0}:${e.colno || 0}`)
  })
  window.addEventListener('unhandledrejection', (e) => {
    log.error('unhandledrejection |', e.reason)
  })
  log.info('MeiKen AI frontend ready')
}
