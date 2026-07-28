import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Paper, Group, Text, Button, Divider, Table, Center, Loader, Modal, Stack, TextInput,
} from '@mantine/core'
import { apiGet, apiSend } from '../api/client'
import { RefSelect } from './RefSelect'

/**
 * TallyDiamoundSection — the demand (دیماند) junction for one tally.
 * A small grid of this tally's diamound entries + an "add" modal that picks a
 * item from the fa_kala_diamound catalog and snapshots its code.
 *
 * Reads:  GET /tally/:id/diamound   (entries, with catalog title/code resolved)
 * Writes: POST/PUT/DELETE /tali-kala-diamound  (the factory router)
 */

type DiamoundRow = {
  id_tali_kala_diamound: number
  tali_id: number
  kala_diamound_id: number | null
  code: string | null        // snapshotted code
  description: string | null
  rate_title: string | null  // from catalog JOIN
  rate_code: string | null    // from catalog JOIN
}

export function TallyDiamoundSection({ tallyId }: { tallyId: number }) {
  const qc = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [rateId, setRateId] = useState<number | null>(null)
  const [snapCode, setSnapCode] = useState<string | null>(null) // code copied from picked rate
  const [description, setDescription] = useState('')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['tally-diamound', tallyId],
    queryFn: () => apiGet<DiamoundRow[]>(`/tally/${tallyId}/diamound`),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      apiSend('/tali-kala-diamound', 'POST', {
        tali_id: tallyId,
        kala_diamound_id: rateId,
        code: snapCode,
        description: description.trim() === '' ? null : description,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tally-diamound', tallyId] })
      setModalOpen(false)
      setRateId(null)
      setSnapCode(null)
      setDescription('')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiSend(`/tali-kala-diamound/${id}`, 'DELETE'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tally-diamound', tallyId] }),
  })

  return (
    <Paper shadow="xs" p="md" mt="md">
      <Group justify="space-between" mb="sm">
        <Text fw={600}>دیماند</Text>
        <Button size="sm" onClick={() => setModalOpen(true)}>افزودن</Button>
      </Group>
      <Divider mb="sm" />

      {isLoading && <Center py="md"><Loader size="sm" /></Center>}
      {isError && <Center py="md"><Text c="red">خطا در بارگذاری.</Text></Center>}

      {data && data.length === 0 && (
        <Center py="md"><Text c="dimmed" size="sm">ردیفی ثبت نشده است.</Text></Center>
      )}

      {data && data.length > 0 && (
        <Table striped withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>کد</Table.Th>
              <Table.Th>عنوان</Table.Th>
              <Table.Th>توضیحات</Table.Th>
              <Table.Th>عملیات</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {data.map((row) => (
              <Table.Tr key={row.id_tali_kala_diamound}>
                <Table.Td>{row.code ?? row.rate_code ?? '—'}</Table.Td>
                <Table.Td>{row.rate_title ?? '—'}</Table.Td>
                <Table.Td>{row.description ?? '—'}</Table.Td>
                <Table.Td>
                  <Button
                    size="xs" variant="light" color="red"
                    onClick={() => deleteMutation.mutate(row.id_tali_kala_diamound)}
                  >
                    حذف
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title="افزودن دیماند">
        <Stack>
          <RefSelect
            label="انتخاب دیماند"
            path="/kala-diamound"
            valueKey="id_kala_diamound"
            labelKey={(r) => `${r.code ?? ''} ${r.title ? `(${r.title})` : ''}`.trim()}
            value={rateId}
            onChange={setRateId}
            onPick={(row) => setSnapCode(row?.code ?? null)}
          />
          <TextInput
            label="توضیحات"
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
          />
          <Group justify="flex-start" mt="sm">
            <Button
              onClick={() => createMutation.mutate()}
              loading={createMutation.isPending}
              disabled={rateId == null}
            >
              ذخیره
            </Button>
            <Button variant="subtle" onClick={() => setModalOpen(false)}>لغو</Button>
          </Group>
        </Stack>
      </Modal>
    </Paper>
  )
}
