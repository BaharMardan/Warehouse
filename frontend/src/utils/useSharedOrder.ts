import { useRef, useState, type HTMLAttributes } from 'react'
import { useMutation } from '@tanstack/react-query'
import { apiSend, errorMessage } from '../api/client'
import { moveItem } from './usePersonalOrder'

export function useSharedOrder<T>(path: string, items: T[], key: (item: T) => string,
  canEdit: boolean, refresh: () => Promise<unknown>) {
  const source = useRef<string | null>(null)
  const [over, setOver] = useState<{ id: string; after: boolean } | null>(null)
  const save = useMutation({
    mutationFn: (ids: string[]) => apiSend(`${path}/display-order`, 'PUT', { ids: ids.map(Number) }),
    onSuccess: async () => { await refresh() },
  })
  const ready = canEdit && !save.isPending
  function move(from: string, to: string, after?: boolean) {
    if (!ready) return
    const ids = items.map(key)
    let next = moveItem(ids, from, to)
    if (after !== undefined && from !== to && ids.includes(from) && ids.includes(to)) {
      next = ids.filter(id => id !== from)
      next.splice(next.indexOf(to) + (after ? 1 : 0), 0, from)
    }
    if (next.some((id, index) => id !== ids[index])) save.mutate(next)
  }
  function itemProps(id: string): HTMLAttributes<HTMLElement> {
    return {
      onDragOver: event => {
        if (!ready || !source.current) return
        event.preventDefault(); event.dataTransfer.dropEffect = 'move'
        const rect = event.currentTarget.getBoundingClientRect()
        setOver({ id, after: event.clientY > rect.top + rect.height / 2 })
      },
      onDrop: event => {
        if (!source.current) return
        event.preventDefault()
        const rect = event.currentTarget.getBoundingClientRect()
        move(source.current, id, event.clientY > rect.top + rect.height / 2)
        source.current = null; setOver(null)
      },
      style: over?.id === id ? { boxShadow: `inset 0 ${over.after ? '-3px' : '3px'} var(--mantine-color-blue-5)` } : undefined,
    }
  }
  function handleProps(id: string): HTMLAttributes<HTMLElement> {
    return {
      draggable: ready,
      onDragStart: event => {
        if (!ready) { event.preventDefault(); return }
        source.current = id; event.dataTransfer.effectAllowed = 'move'
        event.dataTransfer.setData('text/plain', id); event.stopPropagation()
      },
      onDragEnd: () => { source.current = null; setOver(null) },
      style: { cursor: ready ? 'grab' : 'default' },
    }
  }
  function step(id: string, delta: number) {
    const index = items.findIndex(item => key(item) === id)
    const target = items[index + delta]
    if (target) move(id, key(target))
  }
  return { ordered: items, ready, itemProps, handleProps, step, pending: save.isPending,
    error: save.isError ? errorMessage(save.error, 'ذخیرهٔ چینش انجام نشد؛ دوباره تلاش کنید.') : '' }
}
