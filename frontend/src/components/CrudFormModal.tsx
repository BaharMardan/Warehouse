// import { useEffect, useState } from 'react'
// import { Modal, TextInput, NumberInput, Button, Stack } from '@mantine/core'

// export interface FieldDef {
//   key: string
//   label: string
//   type?: 'text' | 'number'
//   required?: boolean
// }

// interface Props {
//   opened: boolean
//   onClose: () => void
//   onSubmit: (values: Record<string, unknown>) => void
//   fields: FieldDef[]
//   initial?: Record<string, any> | null
//   loading?: boolean
//   title: string
// }

// export function CrudFormModal({ opened, onClose, onSubmit, fields, initial, loading, title }: Props) {
//   const [values, setValues] = useState<Record<string, unknown>>({})

//   useEffect(() => {
//     const next: Record<string, unknown> = {}
//     for (const f of fields) next[f.key] = initial?.[f.key] ?? ''
//     setValues(next)
//   }, [initial, opened, fields])

//   const set = (key: string, val: unknown) => setValues((v) => ({ ...v, [key]: val }))
//   const missing = fields.some((f) => f.required && (values[f.key] === '' || values[f.key] == null))

//   // Empty inputs -> null, so optional number columns don't send '' (which breaks
//   // Pydantic float coercion). Required fields are guarded by `missing` above.
//   const submit = () => {
//     const out: Record<string, unknown> = {}
//     for (const f of fields) {
//       const v = values[f.key]
//       out[f.key] = v === '' || v === undefined ? null : v
//     }
//     onSubmit(out)
//   }

//   return (
//     <Modal opened={opened} onClose={onClose} title={title}>
//       <Stack>
//         {fields.map((f) =>
//           f.type === 'number' ? (
//             <NumberInput
//               key={f.key}
//               label={f.label}
//               value={values[f.key] as number | string}
//               onChange={(val) => set(f.key, val)}
//               required={f.required}
//               thousandSeparator=","
//             />
//           ) : (
//             <TextInput
//               key={f.key}
//               label={f.label}
//               value={(values[f.key] as string) ?? ''}
//               onChange={(e) => set(f.key, e.currentTarget.value)}
//               required={f.required}
//             />
//           ),
//         )}
//         <Button onClick={submit} loading={loading} disabled={missing} mt="sm">
//           ذخیره
//         </Button>
//       </Stack>
//     </Modal>
//   )
// }


import { useEffect, useState } from 'react'
import { Modal, TextInput, NumberInput, Button, Stack, Group, Text, Select } from '@mantine/core'
import { RefSelect } from './RefSelect'

type FieldCondition = {
  key: string
  equals: unknown
}

export interface FieldDef {
  key: string
  label: string
  type?: 'text' | 'number' | 'select' | 'reference'
  required?: boolean
  requiredWhen?: FieldCondition
  showWhen?: FieldCondition
  defaultValue?: unknown
  options?: Array<{ value: string; label: string }>
  reference?: {
    path: string
    valueKey: string
    labelKey: string
  }
}

interface Props {
  opened: boolean
  onClose: () => void
  onSubmit: (values: Record<string, unknown>) => void
  fields: FieldDef[]
  initial?: Record<string, any> | null
  loading?: boolean
  error?: string | null
  title: string
}

export function CrudFormModal({
  opened, onClose, onSubmit, fields, initial, loading, error, title,
}: Props) {
  const [values, setValues] = useState<Record<string, unknown>>({})

  useEffect(() => {
    const next: Record<string, unknown> = {}
    for (const f of fields) next[f.key] = initial?.[f.key] ?? f.defaultValue ?? ''
    setValues(next)
  }, [initial, opened, fields])

  const set = (key: string, val: unknown) => setValues((v) => ({ ...v, [key]: val }))
  const matches = (condition?: FieldCondition) =>
    condition == null || String(values[condition.key] ?? '') === String(condition.equals ?? '')
  const visibleFields = fields.filter((f) => matches(f.showWhen))
  const isRequired = (field: FieldDef) =>
    Boolean(field.required || (field.requiredWhen && matches(field.requiredWhen)))
  const missing = visibleFields.some(
    (f) => isRequired(f) && (values[f.key] === '' || values[f.key] == null),
  )

  // Empty inputs -> null, so optional number columns don't send '' (which breaks
  // Pydantic float coercion). Required fields are guarded by `missing` above.
  const submit = () => {
    const out: Record<string, unknown> = {}
    const visibleKeys = new Set(visibleFields.map((field) => field.key))
    for (const f of fields) {
      const v = values[f.key]
      out[f.key] = !visibleKeys.has(f.key) || v === '' || v === undefined ? null : v
    }
    onSubmit(out)
  }

  return (
    <Modal
      opened={opened} onClose={onClose} title={title}
      radius="md" centered size="md" overlayProps={{ backgroundOpacity: 0.55, blur: 2 }}
      styles={{ title: { fontWeight: 700 } }}
    >
      <Stack gap="sm" dir="rtl">
        {visibleFields.map((f) => {
          const required = isRequired(f)
          if (f.type === 'number') return (
            <NumberInput
              key={f.key}
              label={f.label}
              radius="md"
              value={values[f.key] as number | string}
              onChange={(val) => set(f.key, val)}
              required={required}
              thousandSeparator=","
            />
          )
          if (f.type === 'select') return (
            <Select
              key={f.key}
              label={f.label}
              radius="md"
              data={f.options ?? []}
              value={values[f.key] == null || values[f.key] === '' ? null : String(values[f.key])}
              onChange={(value) => set(f.key, value)}
              required={required}
              searchable
              clearable={!required}
              placeholder="انتخاب کنید"
            />
          )
          if (f.type === 'reference' && f.reference) return (
            <RefSelect
              key={f.key}
              label={f.label}
              path={f.reference.path}
              valueKey={f.reference.valueKey}
              labelKey={f.reference.labelKey}
              value={values[f.key] == null || values[f.key] === '' ? null : Number(values[f.key])}
              onChange={(value) => set(f.key, value)}
              required={required}
            />
          )
          return (
            <TextInput
              key={f.key}
              label={f.label}
              radius="md"
              value={(values[f.key] as string) ?? ''}
              onChange={(e) => set(f.key, e.currentTarget.value)}
              required={required}
            />
          )
        })}
        {error && (
          <Text role="alert" c="red" size="sm">
            {error}
          </Text>
        )}
        <Group justify="flex-start" mt="md" gap="sm">
          <Button onClick={submit} loading={loading} disabled={missing} radius="md">
            ذخیره
          </Button>
          <Button variant="default" onClick={onClose} radius="md">
            لغو
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}
