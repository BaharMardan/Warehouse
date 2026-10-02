import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Button, Group, Text, TextInput } from '@mantine/core'
import { apiSend, errorMessage } from '../api/client'
import { usePermissions } from '../auth/usePermissions'
import type { SavedInvoice } from '../pages/invoiceTypes'

export function InvoiceKotazhInput({ invoiceId, saved }: { invoiceId: number; saved: string | null }) {
  const [draft, setDraft] = useState<string | null>(null)
  const cache = useQueryClient()
  const { can } = usePermissions()
  const value = draft ?? saved ?? ''
  const dirty = value.trim() !== (saved ?? '')
  const mutation = useMutation({
    mutationFn: () => apiSend<{ buyer_kotath_code: string | null }>(`/invoice/${invoiceId}/kotazh`, 'PUT', {
      buyer_kotath_code: value.trim() || null,
    }),
    onSuccess: (result) => {
      cache.setQueryData<SavedInvoice>(['invoice', invoiceId], (previous) => previous ? {
        ...previous, header: { ...previous.header, ...result },
      } : previous)
      setDraft(null)
    },
  })
  if (!can('invoice.issue')) return <Text size="sm">شماره کوتاژ: <bdi dir="ltr">{saved || '—'}</bdi></Text>
  return <form onSubmit={(event) => { event.preventDefault(); if (dirty && !mutation.isPending) mutation.mutate() }}>
    <Group mt="md" align="flex-end" gap="xs">
      <TextInput label="افزودن شماره کوتاژ" placeholder="شماره کوتاژ را وارد کنید" dir="ltr"
        value={value} maxLength={250} disabled={mutation.isPending}
        onChange={(event) => { setDraft(event.currentTarget.value); mutation.reset() }}
        style={{ flex: '1 1 180px', maxWidth: 320 }} />
      <Button type="submit" color="red" variant="light" loading={mutation.isPending} disabled={!dirty}>ذخیره</Button>
    </Group>
    {dirty && <Text size="xs" c="dimmed" mt={4}>برای درج در چاپ، شماره کوتاژ را ذخیره کنید.</Text>}
    {mutation.isSuccess && <Text size="xs" c="teal" mt={4}>شماره کوتاژ ذخیره شد.</Text>}
    {mutation.isError && <Text size="xs" c="red" mt={4}>{errorMessage(mutation.error, 'ذخیره شماره کوتاژ ناموفق بود')}</Text>}
  </form>
}
