import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ActionIcon, Alert, Badge, Button, Center, Group, Modal, Paper, Stack, Text, TextInput, Textarea,
  ThemeIcon, Tooltip,
} from '@mantine/core'
import { Inbox, Pencil, Plus, RefreshCw, ShieldCheck, Trash2 } from 'lucide-react'
import { adminApi, adminKeys, errorMessage, type RoleInput, type RoleRow } from '../api/admin'
import { DataTable, type Column } from './DataTable'
import { PermissionChecklist } from './PermissionChecklist'

const EMPTY_ROLE: RoleInput = { title: '', description: null, permissions: [] }

export function RolesPanel() {
  const queryClient = useQueryClient()
  const catalogQuery = useQuery({ queryKey: adminKeys.permissions, queryFn: adminApi.permissions, staleTime: Infinity })
  const rolesQuery = useQuery({ queryKey: adminKeys.roles, queryFn: adminApi.roles })

  const [opened, setOpened] = useState(false)
  const [editing, setEditing] = useState<RoleRow | null>(null)
  const [form, setForm] = useState<RoleInput>(EMPTY_ROLE)

  const labels = useMemo(
    () => new Map((catalogQuery.data ?? []).map((p) => [p.code, p.label])),
    [catalogQuery.data],
  )

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: adminKeys.roles })
    queryClient.invalidateQueries({ queryKey: adminKeys.users }) // users show role titles
  }

  const save = useMutation({
    mutationFn: () => {
      const body = { ...form, description: form.description?.trim() || null }
      return editing ? adminApi.updateRole(editing.id, body) : adminApi.createRole(body)
    },
    onSuccess: () => {
      refresh()
      setOpened(false)
    },
  })
  const remove = useMutation({ mutationFn: (id: number) => adminApi.deleteRole(id), onSuccess: refresh })

  const openAdd = () => {
    save.reset()
    setEditing(null)
    setForm(EMPTY_ROLE)
    setOpened(true)
  }
  const openEdit = (role: RoleRow) => {
    save.reset()
    setEditing(role)
    setForm({ title: role.title, description: role.description, permissions: role.permissions })
    setOpened(true)
  }
  const confirmDelete = (role: RoleRow) => {
    const holders = role.user_count > 0
      ? `\nاین نقش از ${role.user_count.toLocaleString('fa-IR')} کاربر گرفته می‌شود.`
      : ''
    if (confirm(`حذف نقش «${role.title}»؟${holders}`)) remove.mutate(role.id)
  }

  const columns: Column<RoleRow>[] = [
    { key: 'title', label: 'عنوان نقش', render: (role) => <Text fw={600}>{role.title}</Text> },
    { key: 'description', label: 'توضیحات', render: (role) => role.description ?? '—' },
    {
      key: 'permissions', label: 'دسترسی‌ها', render: (role) => role.permissions.length === 0
        ? <Text size="sm" c="dimmed">بدون دسترسی</Text>
        : (
          <Group gap={4}>
            {role.permissions.map((code) => (
              <Badge key={code} variant="light" radius="sm" size="sm">{labels.get(code) ?? code}</Badge>
            ))}
          </Group>
        ),
    },
    { key: 'users', label: 'کاربران', render: (role) => role.user_count.toLocaleString('fa-IR') },
    {
      key: '__actions', label: 'عملیات', render: (role) => (
        <Group gap={4} justify="center" wrap="nowrap">
          <Tooltip label="ویرایش نقش" withArrow>
            <ActionIcon variant="subtle" color="blue" radius="md" aria-label="ویرایش نقش" onClick={() => openEdit(role)}>
              <Pencil size={18} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="حذف نقش" withArrow>
            <ActionIcon
              variant="subtle" color="red" radius="md" aria-label="حذف نقش"
              loading={remove.isPending && remove.variables === role.id}
              onClick={() => confirmDelete(role)}
            >
              <Trash2 size={18} />
            </ActionIcon>
          </Tooltip>
        </Group>
      ),
    },
  ]

  const emptyContent = (
    <Center py={64}>
      <Stack align="center" gap="sm" ta="center" maw={400}>
        <ThemeIcon size={64} radius="xl" variant="light" color="orange"><Inbox size={34} /></ThemeIcon>
        <Text fw={600} size="lg">هنوز نقشی تعریف نشده است</Text>
        <Text size="sm" c="dimmed">
          هر نقش مجموعه‌ای از دسترسی‌هاست، مثل «انباردار» یا «حسابدار». بعد از ساختن نقش، آن را به کاربران بدهید.
        </Text>
        <Button mt="xs" radius="md" leftSection={<Plus size={18} />} onClick={openAdd}>افزودن نقش</Button>
      </Stack>
    </Center>
  )

  return (
    <>
      <Paper radius="md" p="sm" withBorder shadow="xs" mb="md">
        <Group justify="space-between" wrap="wrap" gap="sm">
          <Group gap="xs" wrap="nowrap">
            <ShieldCheck size={18} />
            <Text size="sm" c="dimmed">مدیر سیستم بدون هیچ نقشی به همه بخش‌ها دسترسی دارد.</Text>
          </Group>
          <Group gap="xs">
            <Button
              variant="default" radius="md" leftSection={<RefreshCw size={16} />}
              onClick={refresh} loading={rolesQuery.isFetching && !rolesQuery.isLoading}
            >
              بروزرسانی
            </Button>
            <Button radius="md" leftSection={<Plus size={18} />} onClick={openAdd}>افزودن نقش</Button>
          </Group>
        </Group>
      </Paper>

      {remove.isError && (
        <Alert color="red" radius="md" mb="md" withCloseButton onClose={() => remove.reset()}>
          {errorMessage(remove.error, 'حذف نقش انجام نشد.')}
        </Alert>
      )}

      <DataTable
        columns={columns}
        data={rolesQuery.data}
        isLoading={rolesQuery.isLoading}
        error={rolesQuery.error}
        getRowKey={(role) => role.id}
        emptyContent={emptyContent}
      />

      <Modal
        opened={opened}
        onClose={() => setOpened(false)}
        title={editing ? `ویرایش نقش «${editing.title}»` : 'افزودن نقش'}
        size="lg"
        radius="lg"
        centered
      >
        <Stack gap="md" dir="rtl">
          <TextInput
            label="عنوان نقش"
            placeholder="مثلاً انباردار"
            required
            value={form.title}
            onChange={(event) => setForm({ ...form, title: event.currentTarget.value })}
          />
          <Textarea
            label="توضیحات"
            autosize
            minRows={2}
            value={form.description ?? ''}
            onChange={(event) => setForm({ ...form, description: event.currentTarget.value })}
          />
          <Stack gap={4}>
            <Text fw={600} size="sm">دسترسی‌ها</Text>
            <Text size="xs" c="dimmed">
              بعضی دسترسی‌ها برای کار کردن به دسترسی دیگری نیاز دارند؛ آن‌ها خودکار تیک می‌خورند.
            </Text>
          </Stack>
          {catalogQuery.data
            ? (
              <PermissionChecklist
                catalog={catalogQuery.data}
                value={form.permissions}
                onChange={(permissions) => setForm({ ...form, permissions })}
              />
            )
            : <Text size="sm" c="dimmed">در حال بارگذاری فهرست دسترسی‌ها…</Text>}
          {save.isError && (
            <Alert color="red" radius="md">{errorMessage(save.error, 'ذخیره نقش انجام نشد.')}</Alert>
          )}
          <Group justify="flex-start" gap="sm">
            <Button radius="md" loading={save.isPending} disabled={form.title.trim() === ''} onClick={() => save.mutate()}>
              ذخیره
            </Button>
            <Button variant="default" radius="md" onClick={() => setOpened(false)}>لغو</Button>
          </Group>
        </Stack>
      </Modal>
    </>
  )
}
