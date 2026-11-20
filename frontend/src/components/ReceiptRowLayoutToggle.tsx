import { Checkbox, Stack, Text } from '@mantine/core'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiSend, errorMessage } from '../api/client'
import { usePermissions } from '../auth/usePermissions'

type Layout = { separate_rows: boolean }

export function ReceiptRowLayoutToggle({ tallyId }: { tallyId: number | null }) {
  const qc = useQueryClient()
  const canEdit = usePermissions().can('tally.edit')
  const key = ['tally-receipt-layout', tallyId]
  const path = `/tally-header/${tallyId}/receipt-layout`
  const layout = useQuery({
    queryKey: key,
    queryFn: () => apiGet<Layout>(path),
    enabled: tallyId != null,
  })
  const save = useMutation({
    mutationFn: (separate_rows: boolean) => apiSend<Layout>(path, 'PUT', { separate_rows }),
    onSuccess: async (data) => {
      qc.setQueryData(key, data)
      await Promise.all(['ghabz-details', 'ghabz-print-details', 'receipt-context'].map((name) =>
        qc.invalidateQueries({ queryKey: [name] })))
    },
  })
  return <Stack gap={3} mt={6}>
    <Checkbox size="xs" checked={layout.data?.separate_rows ?? false}
      disabled={!canEdit || !layout.data || save.isPending}
      onChange={(event) => save.mutate(event.currentTarget.checked)}
      label="ردیف‌ها در قبض انبار بر اساس HS Code مشترک جمع نشوند."
      styles={{ label: { fontSize: 11, fontWeight: 400 } }} />
    {layout.error && <Text size="xs" c="red">{errorMessage(layout.error, 'دریافت تنظیم قبض ناموفق بود.')}</Text>}
    {save.error && <Text size="xs" c="red">{errorMessage(save.error, 'ذخیره تنظیم قبض ناموفق بود.')}</Text>}
  </Stack>
}
