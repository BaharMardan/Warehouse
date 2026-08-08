import type { ReactNode, CSSProperties } from 'react'
import { Group, Stack, Title, Text } from '@mantine/core'
import { useLocation } from 'react-router-dom'
import { moduleForPath, accentVars } from '../modules'
import './PageHeader.css'

/**
 * The coloured banner at the top of every inner screen.
 *
 * It reads the `--app-accent-*` vars that AppLayout publishes on the canvas, so
 * a screen reached from the تالی tile is blue, one reached from قبض انبار is
 * teal, and so on — no per-page configuration. Pass `color` only to override.
 *
 * Buttons handed to `actions` sit on a saturated background: use
 * `variant="white"` for the primary action and `variant="default"` (or
 * BackButton) for secondary ones.
 */
interface PageHeaderProps {
  title: string
  subtitle?: string
  actions?: ReactNode
  color?: string
}

export function PageHeader({ title, subtitle, actions, color }: PageHeaderProps) {
  const location = useLocation()
  const mod = moduleForPath(location.pathname)
  const Icon = mod?.icon

  return (
    <div className="ph-band" style={accentVars(color) as CSSProperties}>
      <Group className="ph-inner" justify="space-between" align="flex-end" wrap="wrap" gap="sm">
        <Stack gap={2}>
          {mod && (
            <Group className="ph-eyebrow" gap={6} wrap="nowrap">
              {Icon && <Icon size={14} stroke={2} />}
              <span>{mod.title}</span>
            </Group>
          )}
          <Title order={2} fw={700} c="white">{title}</Title>
          {subtitle && <Text size="sm" c="rgba(255,255,255,0.85)">{subtitle}</Text>}
        </Stack>
        {actions && <Group gap="sm" wrap="wrap">{actions}</Group>}
      </Group>
    </div>
  )
}
