import { Checkbox, Group, SimpleGrid, Stack, Text } from '@mantine/core'
import type { PermissionInfo } from '../api/admin'
import type { PermissionCode } from '../auth/permissions'
import { modules } from '../modules'

/**
 * Codes that `selected` brings in through `implies`, each mapped to the label of
 * a selected permission that brings it. The backend grants these at request
 * time, so they are shown ticked and locked rather than stored on the role.
 */
export function impliedBy(selected: ReadonlySet<string>, catalog: PermissionInfo[]): Map<string, string> {
  const byCode = new Map(catalog.map((p) => [p.code, p]))
  const implied = new Map<string, string>()
  for (const code of selected) {
    const source = byCode.get(code as PermissionCode)
    if (!source) continue
    const pending = [...source.implies]
    while (pending.length > 0) {
      const next = pending.pop()!
      if (selected.has(next) || implied.has(next)) continue
      implied.set(next, source.label)
      pending.push(...(byCode.get(next)?.implies ?? []))
    }
  }
  return implied
}

interface PermissionChecklistProps {
  catalog: PermissionInfo[]
  value: PermissionCode[]
  onChange: (codes: PermissionCode[]) => void
}

/** One group per launcher module, in launcher order, using the module's name and colour. */
export function PermissionChecklist({ catalog, value, onChange }: PermissionChecklistProps) {
  const selected = new Set<string>(value)
  const implied = impliedBy(selected, catalog)
  const groups = modules
    .map((module) => ({ module, items: catalog.filter((p) => p.module === module.key) }))
    .filter((group) => group.items.length > 0)

  const toggle = (code: PermissionCode, checked: boolean) => {
    const next = new Set(selected)
    if (checked) next.add(code)
    else next.delete(code)
    onChange(catalog.map((p) => p.code).filter((c) => next.has(c)))
  }

  return (
    <Stack gap="md">
      {groups.map(({ module, items }) => (
        <Stack key={module.key} gap={8}>
          <Group gap={8}>
            <span
              aria-hidden
              style={{
                width: 10, height: 10, borderRadius: 999,
                background: `var(--mantine-color-${module.color}-6)`,
              }}
            />
            <Text fw={700} size="sm">{module.title}</Text>
          </Group>
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm" verticalSpacing="xs" ps="lg">
            {items.map((p) => {
              const via = selected.has(p.code) ? undefined : implied.get(p.code)
              return (
                <Checkbox
                  key={p.code}
                  label={p.label}
                  description={via ? `همراه با «${via}»` : undefined}
                  checked={selected.has(p.code) || via != null}
                  disabled={via != null}
                  onChange={(event) => toggle(p.code, event.currentTarget.checked)}
                />
              )
            })}
          </SimpleGrid>
        </Stack>
      ))}
    </Stack>
  )
}
