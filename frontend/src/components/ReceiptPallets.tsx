import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Paper, Text } from '@mantine/core'
import { apiGet, apiSend, errorMessage } from '../api/client'
import { usePermissions } from '../auth/usePermissions'
import { PalletRows, type PalletRow, type PalletEntry } from './PalletRows'

type State = { enabled: boolean; editable: boolean; total: number | null; rows: PalletRow[]; resolved: boolean; message: string | null }
export function ReceiptPallets({ id }: { id: number }) {
  const qc = useQueryClient()
  const { can } = usePermissions()
  const query = useQuery({ queryKey: ['receipt-pallets', id], queryFn: () => apiGet<State>(`/ghabz/${id}/pallets`) })
  const save = useMutation({
    mutationFn: (lines: PalletEntry[]) => apiSend(`/ghabz/${id}/pallets`, 'PUT', { lines }),
    onSuccess: async () => { await Promise.all(['receipt-pallets', 'receipt-workflow'].map(key => qc.invalidateQueries({ queryKey: [key] }))) },
  })
  if (query.error) return <Text c="red">{errorMessage(query.error, 'دریافت تخصیص پالت ناموفق بود')}</Text>
  if (!query.data?.enabled) return null
  return <Paper withBorder p="md" my="sm">
    <Text fw={600} mb="sm">پالت ردیف‌های این قبض</Text>
    {query.data.resolved
      ? <Text size="sm" c="dimmed" mb="sm">اطلاعات پالت از تالی و تعداد پالت قبض مشخص است؛ نیازی به ثبت مجدد نیست.</Text>
      : query.data.message && <Text size="sm" c="orange" mb="sm">{query.data.message}</Text>}
    <PalletRows key={id} rows={query.data.rows} allocation expected={query.data.total}
      editable={can('tally.services') && query.data.editable && !query.data.resolved && query.data.total != null}
      pending={save.isPending} onSave={lines => save.mutate(lines)} />
    {query.data.total == null && <Text size="sm" c="orange">ابتدا تعداد پالت قبض تفکیکی را در اطلاعات قبض ثبت کنید.</Text>}
    {save.error && <Text c="red" size="sm">{errorMessage(save.error, 'تخصیص پالت ثبت نشد')}</Text>}
    {save.isSuccess && <Text c="teal" size="sm">تخصیص پالت ذخیره شد.</Text>}
  </Paper>
}
