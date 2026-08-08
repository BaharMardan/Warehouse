import type { CSSProperties } from 'react'
import { SimpleGrid, UnstyledButton, Text, Stack, Box } from '@mantine/core'
import { Link } from 'react-router-dom'
import { BackButton } from '../components/BackButton'
import { PageHeader } from '../components/PageHeader'
import { getBaseDataGroups } from '../modules'
import type { CrudConfig } from '../components/CrudResource'
import './HomePage.css'

/**
 * The «اطلاعات پایه» module. It is a launcher rather than a screen of its own:
 * the 15 simple-CRUD resources are too many for the home page, so they live one
 * level down, grouped by subject.
 *
 * The grouping lives in modules.tsx (`getBaseDataGroups`), which also sweeps any
 * resource that is not explicitly grouped into a trailing «سایر» section — so a
 * newly registered resource can never go missing from the UI.
 */

// One accent colour per group, so the sections read apart at a glance.
const GROUP_COLORS = ['violet', 'teal', 'indigo', 'gray']

function accentVar(color: string): CSSProperties {
  return { '--hp-accent': `var(--mantine-color-${color}-6)` } as CSSProperties
}

function ResourceLink({ resource, color }: { resource: CrudConfig<any>; color: string }) {
  return (
    <UnstyledButton
      component={Link}
      to={resource.route}
      className="hp-link"
      style={accentVar(color)}
    >
      <span className="hp-link-dot" />
      <span className="hp-link-label">{resource.title}</span>
    </UnstyledButton>
  )
}

export function BaseDataPage() {
  const groups = getBaseDataGroups()

  return (
    <Box maw={1100} mx="auto">
      <PageHeader
        title="اطلاعات پایه"
        subtitle="جدول‌های پایه سامانه: کالاها، نرخ‌ها، انبارها و طرف‌حساب‌ها."
        actions={<BackButton to="/" />}
      />

      <Stack gap="xl">
        {groups.map((group, i) => {
          const color = GROUP_COLORS[i % GROUP_COLORS.length]
          return (
            <Stack key={group.title} gap="sm">
              <Text size="xs" fw={700} c="dimmed" style={{ letterSpacing: 0.5 }}>
                {group.title}
              </Text>
              <SimpleGrid cols={{ base: 1, xs: 2, sm: 3, md: 4 }} spacing="sm">
                {group.items.map((r) => (
                  <ResourceLink key={r.route} resource={r} color={color} />
                ))}
              </SimpleGrid>
            </Stack>
          )
        })}
      </Stack>
    </Box>
  )
}

export default BaseDataPage
