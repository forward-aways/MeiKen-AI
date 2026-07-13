const API = import.meta.env.DEV
  ? '/api'
  : '/api'

export const API_BASE = API

export async function get(path) {
  const r = await fetch(API + path, { credentials: 'include' })
  return r.ok ? r.json() : null
}

export async function post(path, body) {
  const r = await fetch(API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body)
  })
  return r.ok ? r.json() : null
}

export async function put(path, body) {
  const r = await fetch(API + path, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body)
  })
  return r.ok ? r.json() : null
}

export async function del(path) {
  return (await fetch(API + path, { method: 'DELETE', credentials: 'include' })).ok
}

export async function fetchRaw(path, init = {}) {
  return fetch(API + path, { ...init, credentials: 'include' })
}
