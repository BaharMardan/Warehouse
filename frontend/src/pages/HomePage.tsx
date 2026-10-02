import type { CSSProperties } from 'react'
import { Badge, SimpleGrid, UnstyledButton, Text, Title, Stack, Box } from '@mantine/core'
import { Link } from 'react-router-dom'
import { useVisibleModules, type AppModule } from '../modules'
import { useAbandoned } from '../api/abandoned'
import './HomePage.css'
import { usePersonalOrder } from '../utils/usePersonalOrder'

/**
 * Odoo-style launcher: one square tile per top-level module, over a full-bleed
 * coloured canvas. The tile list comes from `modules.tsx` — this file never
 * needs editing when a new module is added.
 */

// Mantine colour name -> the two CSS vars the stylesheet reads.
// Declared at module scope (not inside the component) so React never remounts it.
function accentVars(color: string): CSSProperties {
  return {
    '--hp-accent': `var(--mantine-color-${color}-6)`,
    '--hp-accent-light': `var(--mantine-color-${color}-4)`,
  } as CSSProperties
}

function AbandonedBadge() {
  const { data, isError } = useAbandoned()
  if (isError) return <Badge color="red" className="hp-aging-badge" title="دریافت تعداد ناموفق بود">!</Badge>
  if (!data) return null
  return <Badge color="red" className="hp-aging-badge"
    title={`${data.abandoned_count} متروکه، ${data.warning_count} در آستانه متروکه${data.has_unseen ? '؛ موارد جدید' : ''}`}>
    <bdi dir="ltr">{data.total.toLocaleString('fa-IR')}{data.has_unseen ? '+' : ''}</bdi>
  </Badge>
}

function ModuleTile({ module: m }: { module: AppModule }) {
  const Icon = m.icon
  const disabled = m.enabled === false

  const body = (
    <>
      {m.key === 'abandoned' && <AbandonedBadge />}
      <div className="hp-tile-icon">
        <Icon size={34} stroke={1.7} />
      </div>
      <Stack gap={4}>
        <span className="hp-tile-title">{m.title}</span>
        <span className="hp-tile-desc">{m.description}</span>
      </Stack>
      {disabled && <span className="hp-tile-badge">به‌زودی</span>}
    </>
  )

  if (disabled) {
    return (
      <UnstyledButton
        component="div"
        className={`hp-tile hp-tile--${m.key} hp-tile--disabled`}
        style={accentVars(m.color)}
        aria-disabled
        title="این بخش هنوز آماده نشده است"
      >
        {body}
      </UnstyledButton>
    )
  }

  return (
    <UnstyledButton
      component={Link}
      draggable={false}
      to={m.route}
      className={`hp-tile hp-tile--${m.key}`}
      style={accentVars(m.color)}
    >
      {body}
    </UnstyledButton>
  )
}

export function HomePage() {
  const visibleModules = useVisibleModules()
  const order = usePersonalOrder('home', visibleModules, m => m.key)

  return (
    <div className="hp-hero">
      <Box className="hp-hero-inner" maw={1000} mx="auto">
        <Stack gap={4} mb={40} ta="center">
          <Title order={2} className="hp-hero-title">برنامه‌ها</Title>
          <Text size="sm" className="hp-hero-subtitle">
            برای شروع، یکی از بخش‌های زیر را انتخاب کنید.
          </Text>
        </Stack>

        <Text ta="center" size="sm" mb="sm"></Text>
        {order.error && <Text role="alert" c="red" mb="sm">{order.error}</Text>}
        <SimpleGrid cols={{ base: 2, sm: 3, md: 4 }} spacing="lg" verticalSpacing="lg">
          {order.ordered.map((m) => {
            const drag = order.handleProps(m.key)
            const drop = order.itemProps(m.key)
            return <div key={m.key} {...drag} {...drop} style={{ ...drag.style, ...drop.style }}>
              <ModuleTile module={m} />
            </div>
          })}
        </SimpleGrid>
      </Box>
    </div>
  )
}

export default HomePage
