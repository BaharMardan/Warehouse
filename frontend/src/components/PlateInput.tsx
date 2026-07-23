// import { useState, useEffect } from 'react'
// import { Input, Group, TextInput, Select, Text, Box } from '@mantine/core'

// /**
//  * PlateInput — a standard Iranian vehicle license plate entered as its four parts:
//  *
//  *     [ 2 digits ] [ letter ] [ 3 digits ]      ایران [ 2-digit region ]
//  *
//  * Talks a single string to the form, so it drops straight into an existing text
//  * column (no schema change). Serialized as "LL-X-MMM-RR" e.g. "12-ط-345-67";
//  * an empty plate is "". Number boxes accept Persian (۰۱۲۳), Arabic-Indic (٠١٢٣)
//  * and Latin (0123) digits and store Latin.
//  *
//  *   <PlateInput label="شماره حامل" value={line.type_number_kantiner}
//  *               onChange={(v) => set('type_number_kantiner', v)} />
//  */

// // Letters used on Iranian plates, in Persian-alphabet order. Trim/extend as needed.
// const PLATE_LETTERS = [
//   'الف', 'ب', 'پ', 'ت', 'ث', 'ج', 'د', 'ز', 'ژ', 'س', 'ش', 'ص',
//   'ط', 'ع', 'ف', 'ق', 'ک', 'گ', 'ل', 'م', 'ن', 'و', 'ه', 'ی',
// ]

// type Parts = { l2: string; letter: string; m3: string; r2: string }
// const EMPTY: Parts = { l2: '', letter: '', m3: '', r2: '' }

// // Persian/Arabic-Indic digits -> Latin. Latin passes through.
// function normalizeDigits(s: string): string {
//   return s
//     .replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
//     .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
// }

// // "12-ط-345-67" -> parts. Anything that isn't our 4-part digit/letter shape -> empty,
// // so legacy free-text already stored in the column doesn't mis-populate the boxes.
// function parse(value: string): Parts {
//   const p = (value ?? '').split('-')
//   if (p.length === 4) {
//     const [l2, letter, m3, r2] = p
//     if (/^\d{0,2}$/.test(l2) && /^\d{0,3}$/.test(m3) && /^\d{0,2}$/.test(r2)) {
//       return { l2, letter, m3, r2 }
//     }
//   }
//   return { ...EMPTY }
// }

// function serialize(p: Parts): string {
//   if (!p.l2 && !p.letter && !p.m3 && !p.r2) return ''
//   return `${p.l2}-${p.letter}-${p.m3}-${p.r2}`
// }

// type Props = {
//   value: string
//   onChange: (value: string) => void
//   label?: string
//   required?: boolean
// }

// export function PlateInput({ value, onChange, label, required }: Props) {
//   // Local box strings so the user can type freely; resync if the parent changes value.
//   const [parts, setParts] = useState<Parts>(() => parse(value))
//   useEffect(() => { setParts(parse(value)) }, [value])

//   function update(next: Parts) {
//     setParts(next)
//     onChange(serialize(next))
//   }

//   const digits = (s: string, max: number) =>
//     normalizeDigits(s).replace(/\D/g, '').slice(0, max)

//   const numBox = {
//     inputMode: 'numeric' as const,
//     styles: { input: { textAlign: 'center' as const } },
//   }

//   return (
//     <Input.Wrapper label={label} required={required}>
//       {/* dir=ltr: the plate reads left-to-right, region box last (like the physical plate) */}
//       <Group gap={6} wrap="nowrap" mt={4} align="center" dir="ltr">
//         <TextInput
//           {...numBox} w={58} placeholder="۱۲" value={parts.l2}
//           onChange={(e) => update({ ...parts, l2: digits(e.currentTarget.value, 2) })}
//         />
//         <Select
//           w={84} placeholder="حرف" data={PLATE_LETTERS} searchable clearable
//           value={parts.letter || null}
//           onChange={(v) => update({ ...parts, letter: v ?? '' })}
//         />
//         <TextInput
//           {...numBox} w={72} placeholder="۳۴۵" value={parts.m3}
//           onChange={(e) => update({ ...parts, m3: digits(e.currentTarget.value, 3) })}
//         />
//         {/* the blue "ایران" strip that sits beside the region code on real plates */}
//         <Box
//           h={36} miw={38} px={6}
//           style={{
//             background: '#12358f', borderRadius: 4,
//             display: 'flex', alignItems: 'center', justifyContent: 'center',
//           }}
//         >
//           <Text size="10px" fw={700} c="white">ایران</Text>
//         </Box>
//         <TextInput
//           {...numBox} w={58} placeholder="۶۷" value={parts.r2}
//           onChange={(e) => update({ ...parts, r2: digits(e.currentTarget.value, 2) })}
//         />
//       </Group>
//     </Input.Wrapper>
//   )
// }

import { useState, useEffect } from 'react'
import { Input, Group, TextInput, Select, Text, Box, ActionIcon } from '@mantine/core'

/**
 * PlateInput — a standard Iranian vehicle license plate entered as its four parts:
 *
 *     [ 2 digits ] [ letter ] [ 3 digits ]      ایران [ 2-digit region ]
 *
 * Talks a single string to the form, so it drops straight into an existing text
 * column (no schema change). Serialized as "LL-X-MMM-RR|FOREIGN_PLATE" 
 * e.g. "12-ط-345-67|TR-34-ABC". An empty plate is "". Number boxes accept 
 * Persian (۰۱۲۳), Arabic-Indic (٠١٢٣) and Latin (0123) digits and store Latin.
 */

// Letters used on Iranian plates, in Persian-alphabet order. Trim/extend as needed.
const PLATE_LETTERS = [
  'الف', 'ب', 'پ', 'ت', 'ث', 'ج', 'د', 'ز', 'ژ', 'س', 'ش', 'ص',
  'ط', 'ع', 'ف', 'ق', 'ک', 'گ', 'ل', 'م', 'ن', 'و', 'ه', 'ی',
]

type Parts = { l2: string; letter: string; m3: string; r2: string; foreign: string }
const EMPTY: Parts = { l2: '', letter: '', m3: '', r2: '', foreign: '' }

// Persian/Arabic-Indic digits -> Latin. Latin passes through.
function normalizeDigits(s: string): string {
  return s
    .replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
    .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
}

// "12-ط-345-67|TR-34" -> parts. 
function parse(value: string): Parts {
  const [iranPart, foreignPart] = (value ?? '').split('|')
  const p = (iranPart ?? '').split('-')
  const result: Parts = { ...EMPTY, foreign: foreignPart || '' }
  
  if (p.length === 4) {
    const [l2, letter, m3, r2] = p
    if (/^\d{0,2}$/.test(l2) && /^\d{0,3}$/.test(m3) && /^\d{0,2}$/.test(r2)) {
      result.l2 = l2
      result.letter = letter
      result.m3 = m3
      result.r2 = r2
    }
  }
  return result
}

function serialize(p: Parts): string {
  const hasIran = Boolean(p.l2 || p.letter || p.m3 || p.r2)
  const iranStr = hasIran ? `${p.l2}-${p.letter}-${p.m3}-${p.r2}` : ''
  
  if (p.foreign && iranStr) return `${iranStr}|${p.foreign}`
  if (p.foreign) return `|${p.foreign}`
  return iranStr
}

type Props = {
  value: string
  onChange: (value: string) => void
  label?: string
  required?: boolean
}

export function PlateInput({ value, onChange, label, required }: Props) {
  const [parts, setParts] = useState<Parts>(() => parse(value))
  const [showForeign, setShowForeign] = useState(() => !!parse(value).foreign)

  useEffect(() => { 
    const parsed = parse(value)
    setParts(parsed) 
    setShowForeign(!!parsed.foreign)
  }, [value])

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
        
        {/* Updated Iranian Flag Box */}
        <Box
          h={36} miw={38}
          style={{
            borderRadius: 4,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            border: '1px solid #ced4da'
          }}
        >
          <Box style={{ height: '33%', width: '100%', backgroundColor: '#16a34a' }} />
          <Box style={{ height: '34%', width: '100%', backgroundColor: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Text size="10px" fw={700} c="black" style={{ lineHeight: 1 }}>ایران</Text>
          </Box>
          <Box style={{ height: '33%', width: '100%', backgroundColor: '#dc2626' }} />
        </Box>

        <TextInput
          {...numBox} w={58} placeholder="۶۷" value={parts.r2}
          onChange={(e) => update({ ...parts, r2: digits(e.currentTarget.value, 2) })}
        />

        {/* Add Foreign Plate Button */}
        {!showForeign && (
          <ActionIcon 
            variant="default" 
            size={36} 
            onClick={() => setShowForeign(true)}
            title="افزودن پلاک خارجی"
            ml={4}
          >
            <Text size="xl" mt={-2}>+</Text>
          </ActionIcon>
        )}
      </Group>

      {/* Dynamic Foreign Plate Input */}
      {showForeign && (
        <Group mt="sm" dir="rtl" wrap="nowrap" align="flex-end">
          <TextInput
            label="پلاک خارجی"
            placeholder="e.g. TR-34-ABC-123"
            dir="ltr"
            style={{ flex: 1 }}
            value={parts.foreign}
            onChange={(e) => {
              // Restrict to letters, numbers, spaces, and hyphens
              const val = e.currentTarget.value.replace(/[^a-zA-Z0-9\s\-]/g, '');
              update({ ...parts, foreign: val });
            }}
          />
          <ActionIcon 
            color="red" 
            variant="light" 
            size={36} 
            mb={2} 
            onClick={() => {
              setShowForeign(false);
              update({ ...parts, foreign: '' });
            }}
            title="حذف پلاک خارجی"
          >
            <Text size="md">✕</Text>
          </ActionIcon>
        </Group>
      )}
    </Input.Wrapper>
  )
}