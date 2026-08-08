import type { CSSProperties } from 'react'
import { SimpleGrid, UnstyledButton, Text, Title, Stack, Box } from '@mantine/core'
import { Link } from 'react-router-dom'
import { modules, type AppModule } from '../modules'
import './HomePage.css'

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

function ModuleTile({ module: m }: { module: AppModule }) {
  const Icon = m.icon
  const disabled = m.enabled === false

  const body = (
    <>
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
        className="hp-tile hp-tile--disabled"
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
      to={m.route}
      className="hp-tile"
      style={accentVars(m.color)}
    >
      {body}
    </UnstyledButton>
  )
}

export function HomePage() {
  return (
    <div className="hp-hero">
      <Box className="hp-hero-inner" maw={1000} mx="auto">
        <Stack gap={4} mb={40} ta="center">
          <Title order={2} className="hp-hero-title">برنامه‌ها</Title>
          <Text size="sm" className="hp-hero-subtitle">
            برای شروع، یکی از بخش‌های زیر را انتخاب کنید.
          </Text>
        </Stack>

        <SimpleGrid cols={{ base: 2, sm: 3, md: 4 }} spacing="lg" verticalSpacing="lg">
          {modules.map((m) => (
            <ModuleTile key={m.key} module={m} />
          ))}
        </SimpleGrid>
      </Box>
    </div>
  )
}

export default HomePage