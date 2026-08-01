// import { Grid, Select, TextInput } from '@mantine/core'

// /**
//  * ContainerFields — the tally line's «نوع کانتینر» (container type) dropdown plus a
//  * «شماره کانتینر» (container number) box that only appears for the two container
//  * types (۲۰/۴۰ فوت). The number accepts English letters and digits only.
//  *
//  * Fully controlled: the parent owns both string values.
//  *   <ContainerFields
//  *      type={line.container_type} number={line.container_number}
//  *      onTypeChange={(v) => set('container_type', v)}
//  *      onNumberChange={(v) => set('container_number', v)} />
//  */

// // In the exact order requested.
// const CONTAINER_TYPES = [
//   '۴۰ فوت', '۲۰ فوت', 'تریلی چادری', 'تریلی یخچال‌دار',
//   'کامیون جفت', 'خاور', 'وانت', 'کمرشکن',
// ]

// // The types that carry a container number.
// const TYPES_WITH_NUMBER = ['۲۰ فوت', '۴۰ فوت']

// type Props = {
//   type: string
//   number: string
//   onTypeChange: (value: string) => void
//   onNumberChange: (value: string) => void
// }

// export function ContainerFields({ type, number, onTypeChange, onNumberChange }: Props) {
//   const showNumber = TYPES_WITH_NUMBER.includes(type)

//   function handleType(v: string | null) {
//     const next = v ?? ''
//     onTypeChange(next)
//     // clear the number when switching to a type that doesn't carry one
//     if (!TYPES_WITH_NUMBER.includes(next)) onNumberChange('')
//   }

//   // English letters + digits only (e.g. ISO container codes like MSKU1234567)
//   const alnum = (s: string) => s.replace(/[^A-Za-z0-9]/g, '')

//   return (
//     <>
//       <Grid.Col span={6}>
//         <Select
//           label="نوع کانتینر"
//           placeholder="انتخاب کنید"
//           data={CONTAINER_TYPES}
//           value={type || null}
//           onChange={handleType}
//           searchable
//           clearable
//         />
//       </Grid.Col>
//       {showNumber && (
//         <Grid.Col span={6}>
//           <TextInput
//             label="شماره کانتینر"
//             value={number}
//             onChange={(e) => onNumberChange(alnum(e.currentTarget.value))}
//             placeholder="ABCD1234567"
//           />
//         </Grid.Col>
//       )}
//     </>
//   )
// }

import { Grid, Select, TextInput } from '@mantine/core'

/**
 * ContainerFields — the tally line's «نوع کانتینر» (container type) dropdown plus a
 * «شماره کانتینر» (container number) box that only appears for the two container
 * types (۲۰/۴۰ فوت). The number accepts English letters and digits only.
 *
 * Fully controlled: the parent owns both string values.
 *   <ContainerFields
 *      type={line.container_type} number={line.container_number}
 *      onTypeChange={(v) => set('container_type', v)}
 *      onNumberChange={(v) => set('container_number', v)} />
 */

// In the exact order requested.
// Exported so the inline goods grid reuses the exact same option list instead of
// keeping a second copy that can silently drift.
export const CONTAINER_TYPES = [
  '۴۰ فوت', '۲۰ فوت', 'تریلی چادری', 'تریلی یخچال‌دار',
  'کامیون جفت', 'خاور', 'وانت', 'کمرشکن',
]

// The types that carry a container number.
export const TYPES_WITH_NUMBER = ['۲۰ فوت', '۴۰ فوت']

type Props = {
  type: string
  number: string
  onTypeChange: (value: string) => void
  onNumberChange: (value: string) => void
}

export function ContainerFields({ type, number, onTypeChange, onNumberChange }: Props) {
  const showNumber = TYPES_WITH_NUMBER.includes(type)

  function handleType(v: string | null) {
    const next = v ?? ''
    onTypeChange(next)
    // clear the number when switching to a type that doesn't carry one
    if (!TYPES_WITH_NUMBER.includes(next)) onNumberChange('')
  }

  // English letters + digits only (e.g. ISO container codes like MSKU1234567)
  const alnum = (s: string) => s.replace(/[^A-Za-z0-9]/g, '')

  return (
    <>
      <Grid.Col span={6}>
        <Select
          label="نوع کانتینر"
          placeholder="انتخاب کنید"
          data={CONTAINER_TYPES}
          value={type || null}
          onChange={handleType}
          searchable
          clearable
        />
      </Grid.Col>
      {showNumber && (
        <Grid.Col span={6}>
          <TextInput
            label="شماره کانتینر"
            value={number}
            onChange={(e) => onNumberChange(alnum(e.currentTarget.value))}
            placeholder="ABCD1234567"
          />
        </Grid.Col>
      )}
    </>
  )
}