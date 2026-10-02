import { useEffect, useRef, useState, type HTMLAttributes } from 'react'
import { useCurrentUser } from '../auth/usePermissions'

export function orderedItems<T>(items: T[], order: string[], key: (item: T) => string): T[] {
  const ranks = new Map(order.map((id, index) => [id, index]))
  return [...items].sort((a, b) => (ranks.get(key(a)) ?? order.length) - (ranks.get(key(b)) ?? order.length))
}

export function moveItem(ids: string[], source: string, target: string): string[] {
  const from = ids.indexOf(source), to = ids.indexOf(target)
  if (from < 0 || to < 0 || from === to) return ids
  const next = [...ids]
  next.splice(from, 1)
  next.splice(to, 0, source)
  return next
}

function readOrder(key: string | null): string[] {
  if (!key) return []
  try {
    const value: unknown = JSON.parse(localStorage.getItem(key) ?? '[]')
    return Array.isArray(value) ? [...new Set(value.filter((id): id is string => typeof id === 'string'))] : []
  } catch { return [] }
}

export function usePersonalOrder<T>(scope: string, items: T[], key: (item: T) => string) {
  const { data: user } = useCurrentUser()
  const storageKey = user ? `warehouse:order:v1:${user.id}:${scope}` : null
  const [saved, setSaved] = useState<{ key: string | null; order: string[] }>({ key: null, order: [] })
  const [error, setError] = useState('')
  const [over, setOver] = useState<string | null>(null)
  const source = useRef<string | null>(null)
  useEffect(() => {
    setSaved({ key: storageKey, order: readOrder(storageKey) })
    setError('')
    source.current = null
    setOver(null)
  }, [storageKey])
  const order = saved.key === storageKey ? saved.order : readOrder(storageKey)
  const ordered = orderedItems(items, order, key)
  function move(from: string, to: string) {
    if (!storageKey) return
    const ids = ordered.map(key)
    const next = moveItem(ids, from, to)
    if (next === ids) return
    // Keep temporarily hidden items (permissions or filters) in the saved order.
    const all = [...next, ...order.filter(id => !ids.includes(id))]
    setSaved({ key: storageKey, order: all })
    try { localStorage.setItem(storageKey, JSON.stringify(all)); setError('') }
    catch { setError('ذخیرهٔ چینش در مرورگر ممکن نشد؛ تغییر فقط تا خروج از صفحه باقی می‌ماند.') }
  }
  function reset() {
    if (!storageKey) return
    try { localStorage.removeItem(storageKey); setSaved({ key: storageKey, order: [] }); setError('') }
    catch { setError('بازنشانی چینش ممکن نشد.') }
  }
  function itemProps(id: string): HTMLAttributes<HTMLElement> {
    return {
      onDragOver: event => {
        if (!source.current) return
        event.preventDefault()
        event.dataTransfer.dropEffect = 'move'
        setOver(id)
      },
      onDrop: event => {
        if (!source.current) return
        event.preventDefault()
        move(source.current, id)
        source.current = null
        setOver(null)
      },
      style: over === id ? { outline: '2px dashed var(--mantine-color-blue-5)', outlineOffset: -2 } : undefined,
    }
  }
  function handleProps(id: string): HTMLAttributes<HTMLElement> {
    return {
      draggable: !!storageKey,
      onDragStart: event => {
        source.current = id
        event.dataTransfer.effectAllowed = 'move'
        event.dataTransfer.setData('text/plain', id)
        event.stopPropagation()
      },
      onDragEnd: () => { source.current = null; setOver(null) },
      onKeyDown: event => {
        if (event.key === 'Escape') { source.current = null; setOver(null) }
      },
      style: { cursor: 'grab' },
    }
  }
  function step(id: string, delta: number) {
    const index = ordered.findIndex(item => key(item) === id)
    const target = ordered[index + delta]
    if (target) move(id, key(target))
  }
  return { ordered, error, reset, itemProps, handleProps, step, ready: !!storageKey }
}
