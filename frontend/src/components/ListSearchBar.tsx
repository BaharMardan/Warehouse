import { Paper, TextInput } from '@mantine/core'
import { IconSearch } from './icons'

export function ListSearchBar({ value, onChange, placeholder }: {
  value: string; onChange: (value: string) => void; placeholder: string
}) {
  return (
    <Paper radius="md" p="sm" withBorder shadow="xs" mb="md"
      bg="var(--app-accent-light, var(--mantine-color-gray-0))"
      style={{ borderColor: 'var(--app-accent-light-hover, var(--mantine-color-gray-3))' }}>
      <TextInput radius="md" placeholder={placeholder} leftSection={<IconSearch size={16} />}
        value={value} onChange={event => onChange(event.currentTarget.value)} />
    </Paper>
  )
}
