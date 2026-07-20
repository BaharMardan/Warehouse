import { useState, useEffect } from 'react'
import { Input, Group, TextInput, Select, Text, Box } from '@mantine/core'

/**
 * PlateInput — a standard Iranian vehicle license plate entered as its four parts:
 *
 *     [ 2 digits ] [ letter ] [ 3 digits ]      ایران [ 2-digit region ]
 *
 * Talks a single string to the form, so it drops straight into an existing text
 * column (no schema change). Serialized as "LL-X-MMM-RR" e.g. "12-ط-345-67";
 * an empty plate is "". Number boxes accept Persian (۰۱۲۳), Arabic-Indic (٠١٢٣)
 * and Latin (0123) digits and store Latin.
 *
 *   <PlateInput label="شماره حامل" value={line.type_number_kantiner}
 *               onChange={(v) => set('type_number_kantiner', v)} />
 */

// Letters used on Iranian plates, in Persian-alphabet order. Trim/extend as needed.
const PLATE_LETTERS = [
  'الف', 'ب', 'پ', 'ت', 'ث', 'ج', 'د', 'ز', 'ژ', 'س', 'ش', 'ص',
  'ط', 'ع', 'ف', 'ق', 'ک', 'گ', 'ل', 'م', 'ن', 'و', 'ه', 'ی',
]

type Parts = { l2: string; letter: string; m3: string; r2: string }
const EMPTY: Parts = { l2: '', letter: '', m3: '', r2: '' }

// Persian/Arabic-Indic digits -> Latin. Latin passes through.
function normalizeDigits(s: string): string {
  return s
    .replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
    .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
}

// "12-ط-345-67" -> parts. Anything that isn't our 4-part digit/letter shape -> empty,
// so legacy free-text already stored in the column doesn't mis-populate the boxes.
function parse(value: string): Parts {
  const p = (value ?? '').split('-')
  if (p.length === 4) {
    const [l2, letter, m3, r2] = p
    if (/^\d{0,2}$/.test(l2) && /^\d{0,3}$/.test(m3) && /^\d{0,2}$/.test(r2)) {
      return { l2, letter, m3, r2 }
    }
  }
  return { ...EMPTY }
}

function serialize(p: Parts): string {
  if (!p.l2 && !p.letter && !p.m3 && !p.r2) return ''
  return `${p.l2}-${p.letter}-${p.m3}-${p.r2}`
}

type Props = {
  value: string
  onChange: (value: string) => void
  label?: string
  required?: boolean
}

export function PlateInput({ value, onChange, label, required }: Props) {
  // Local box strings so the user can type freely; resync if the parent changes value.
  const [parts, setParts] = useState<Parts>(() => parse(value))
  useEffect(() => { setParts(parse(value)) }, [value])

  function update(next: Parts) {
    setParts(next)
    onChange(serialize(next))
  }

  const digits = (s: string, max: number) =>
    normalizeDigits(s).replace(/\D/g, '').slice(0, max)

  const numBox = {
    inputMode: 'numeric' as const,
    styles: { input: { textAlign: 'center' as const } },
  }

  return (
    <Input.Wrapper label={label} required={required}>
      {/* dir=ltr: the plate reads left-to-right, region box last (like the physical plate) */}
      <Group gap={6} wrap="nowrap" mt={4} align="center" dir="ltr">
        <TextInput
          {...numBox} w={58} placeholder="۱۲" value={parts.l2}
          onChange={(e) => update({ ...parts, l2: digits(e.currentTarget.value, 2) })}
        />
        <Select
          w={84} placeholder="حرف" data={PLATE_LETTERS} searchable clearable
          value={parts.letter || null}
          onChange={(v) => update({ ...parts, letter: v ?? '' })}
        />
        <TextInput
          {...numBox} w={72} placeholder="۳۴۵" value={parts.m3}
          onChange={(e) => update({ ...parts, m3: digits(e.currentTarget.value, 3) })}
        />
        {/* the blue "ایران" strip that sits beside the region code on real plates */}
        <Box
          h={36} miw={38} px={6}
          style={{
            background: '#12358f', borderRadius: 4,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <Text size="10px" fw={700} c="white">ایران</Text>
        </Box>
        <TextInput
          {...numBox} w={58} placeholder="۶۷" value={parts.r2}
          onChange={(e) => update({ ...parts, r2: digits(e.currentTarget.value, 2) })}
        />
      </Group>
    </Input.Wrapper>
  )
}