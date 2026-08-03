// import { Text } from '@mantine/core'
// import { CommoditySelect, type Commodity } from './CommoditySelect'
// import { StorageGroupSelect } from './StorageGroupSelect'

// export type { Commodity }

// /**
//  * CommodityPicker — the ONE commodity-entry control, shared by Tally and Ghabz (and any
//  * future screen). The commodity catalog (FA_COMMODITY_CATALOG) is the single source of
//  * truth, so both screens search + autofill identically instead of keeping their own logic.
//  *
//  * Behaviour:
//  *   - search by HS code or Persian description, pick a commodity;
//  *   - onPick hands the full catalog row to the parent, which snapshots whichever of
//  *     description / HS / unit / duty / profit its own line columns actually have;
//  *   - the storage-price group (code_groupe_kala / code_kala) is resolved automatically
//  *     when the commodity is mapped (STORAGE_GROUP_ID) and the picker is hidden; otherwise
//  *     a named group dropdown is shown as a fallback — the user never types a raw number.
//  *
//  * The parent owns `picked` (so it can reset it when the modal opens) and the group value
//  * (so it lives in the line payload). Invoice calc still reads code_groupe_kala unchanged.
//  */

// type Props = {
//   /** currently selected catalog row (parent-owned, reset on modal open) */
//   picked: Commodity | null
//   /** fired on select/clear — parent snapshots the descriptive fields it has columns for */
//   onPick: (c: Commodity | null) => void
//   /** current storage-group id = the line's code_groupe_kala / code_kala */
//   groupValue: number | null
//   /** set when a mapped commodity auto-resolves the group, or when picked manually */
//   onGroupChange: (id: number | null) => void
//   label?: string
// }

// export function CommodityPicker({ picked, onPick, groupValue, onGroupChange, label }: Props) {
//   const autoGroup = picked?.storage_group_id != null

//   return (
//     <>
//       <CommoditySelect
//         label={label ?? 'جستجوی کالا از کاتالوگ'}
//         value={picked?.id ?? null}
//         selected={picked}
//         onPick={(c) => {
//           onPick(c)
//           // mapped commodity -> resolve the storage group automatically
//           if (c?.storage_group_id != null) onGroupChange(c.storage_group_id)
//         }}
//       />

//       {picked && (
//         <Text size="sm" c="dimmed">
//           واحد: {picked.unit ?? '—'} | حقوق گمرکی: {picked.customs_duty ?? '—'} | سود بازرگانی: {picked.commercial_profit ?? '—'}
//         </Text>
//       )}

//       {autoGroup ? (
//         <Text size="sm" c="teal">گروه قیمت انبار به‌صورت خودکار از کاتالوگ تعیین شد.</Text>
//       ) : (
//         <StorageGroupSelect
//           label="گروه قیمت انبار"
//           required
//           description={picked ? 'این کالا در کاتالوگ به گروه قیمت وصل نشده؛ گروه را انتخاب کنید.' : undefined}
//           value={groupValue}
//           onChange={onGroupChange}
//         />
//       )}
//     </>
//   )
// }

import { Text, type SelectProps } from '@mantine/core'
import { CommoditySelect, type Commodity } from './CommoditySelect'
import { StorageGroupSelect } from './StorageGroupSelect'

export type { Commodity }

/**
 * CommodityPicker — the ONE commodity-entry control, shared by Tally and Ghabz (and any
 * future screen). The commodity catalog (FA_COMMODITY_CATALOG) is the single source of
 * truth, so both screens search + autofill identically instead of keeping their own logic.
 *
 * Behaviour:
 *   - search by HS code or Persian description, pick a commodity;
 *   - onPick hands the full catalog row to the parent, which snapshots whichever of
 *     description / HS / unit / duty / profit its own line columns actually have;
 *   - the storage-price group (code_groupe_kala / code_kala) is resolved automatically
 *     when the commodity is mapped (STORAGE_GROUP_ID) and the picker is hidden; otherwise
 *     a named group dropdown is shown as a fallback — the user never types a raw number.
 *
 * The parent owns `picked` (so it can reset it when the modal opens) and the group value
 * (so it lives in the line payload). Invoice calc still reads code_groupe_kala unchanged.
 */

type Props = {
  /** currently selected catalog row (parent-owned, reset on modal open) */
  picked: Commodity | null
  /** fired on select/clear — parent snapshots the descriptive fields it has columns for */
  onPick: (c: Commodity | null) => void
  /** current storage-group id = the line's code_groupe_kala / code_kala */
  groupValue: number | null
  /** set when a mapped commodity auto-resolves the group, or when picked manually */
  onGroupChange: (id: number | null) => void
  label?: string
  /**
   * Forwarded to both dropdowns. Inside a Popover pass { withinPortal: false }: a
   * portaled dropdown lives outside the popover DOM, so picking an option counts as a
   * click outside and closes the popover before the group can be set.
   */
  comboboxProps?: SelectProps['comboboxProps']
}

export function CommodityPicker({ picked, onPick, groupValue, onGroupChange, label, comboboxProps }: Props) {
  const autoGroup = picked?.storage_group_id != null

  return (
    <>
      <CommoditySelect
        label={label ?? 'جستجوی کالا از کاتالوگ'}
        value={picked?.id ?? null}
        selected={picked}
        comboboxProps={comboboxProps}
        onPick={(c) => {
          onPick(c)
          // mapped commodity -> resolve the storage group automatically
          if (c?.storage_group_id != null) onGroupChange(c.storage_group_id)
        }}
      />

      {picked && (
        <Text size="sm" c="dimmed">
          واحد: {picked.unit ?? '—'} | حقوق گمرکی: {picked.customs_duty ?? '—'} | سود بازرگانی: {picked.commercial_profit ?? '—'}
        </Text>
      )}

      {autoGroup ? (
        <Text size="sm" c="teal">گروه قیمت انبار به‌صورت خودکار از کاتالوگ تعیین شد.</Text>
      ) : (
        <StorageGroupSelect
          label="گروه قیمت انبار"
          description={picked ? 'این کالا در کاتالوگ به گروه قیمت وصل نشده؛ در صورت نیاز گروه را انتخاب کنید.' : undefined}
          value={groupValue}
          onChange={onGroupChange}
          comboboxProps={comboboxProps}
        />
      )}
    </>
  )
}
