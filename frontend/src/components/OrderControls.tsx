import type { HTMLAttributes } from 'react'
import { ActionIcon, Group } from '@mantine/core'

export function OrderControls({ handle, previous, next, label }: {
  handle: HTMLAttributes<HTMLElement>; previous?: () => void; next?: () => void; label: string
}) {
  return <Group gap={2} wrap="nowrap" justify="center">
    <ActionIcon variant="subtle" color="gray" {...handle}
      aria-label={`جابه‌جایی ${label}`} title="برای جابه‌جایی بکشید">
      <span aria-hidden>⠿</span>
    </ActionIcon>
    <ActionIcon variant="subtle" color="gray" size="sm" disabled={!previous}
      onClick={previous} aria-label={`انتقال ${label} به قبل`} title="انتقال به قبل">↑</ActionIcon>
    <ActionIcon variant="subtle" color="gray" size="sm" disabled={!next}
      onClick={next} aria-label={`انتقال ${label} به بعد`} title="انتقال به بعد">↓</ActionIcon>
  </Group>
}
