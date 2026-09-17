import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ActionIcon, Alert, Badge, Button, Center, Group, Modal, MultiSelect, Paper, PasswordInput, Stack,
  Switch, Text, TextInput, ThemeIcon, Tooltip,
} from '@mantine/core'
import { Inbox, KeyRound, Pencil, RefreshCw, Search, UserPlus } from 'lucide-react'
import { adminApi, adminKeys, errorMessage, type UserRow } from '../api/admin'
import { usePermissions } from '../auth/usePermissions'
import { DataTable, type Column } from './DataTable'

interface UserForm {
  username: string
  password: string
  full_name: string
  is_admin: boolean
  is_active: boolean
  role_ids: string[] // MultiSelect works with strings
}

const EMPTY_USER: UserForm = {
  username: '', password: '', full_name: '', is_admin: false, is_active: true, role_ids: [],
}
const PASSWORD_MIN = 8

// Persian/Arabic-Indic digits -> Latin so a search matches either script.
const normalizeDigits = (s: string) =>
  s.replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
    .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))

export function UsersPanel() {
  const queryClient = useQueryClient()
  const { user: me } = usePermissions()
  const usersQuery = useQuery({ queryKey: adminKeys.users, queryFn: adminApi.users })
  const rolesQuery = useQuery({ queryKey: adminKeys.roles, queryFn: adminApi.roles })

  const [search, setSearch] = useState('')
  const [formOpened, setFormOpened] = useState(false)
  const [editing, setEditing] = useState<UserRow | null>(null)
  const [form, setForm] = useState<UserForm>(EMPTY_USER)
  const [passwordUser, setPasswordUser] = useState<UserRow | null>(null)
  const [password, setPassword] = useState('')
  const [passwordAgain, setPasswordAgain] = useState('')
  const [notice, setNotice] = useState<string | null>(null)

  const editingSelf = editing != null && editing.id === me?.id

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: adminKeys.users })
    queryClient.invalidateQueries({ queryKey: adminKeys.roles }) // user counts per role
    queryClient.invalidateQueries({ queryKey: ['current-user'] }) // the header shows my own name
  }

  const save = useMutation({
    mutationFn: () => {
      const common = {
        full_name: form.full_name.trim() || null,
        is_admin: form.is_admin ? 'yes' as const : 'no' as const,
        is_active: form.is_active ? 'yes' as const : 'no' as const,
        role_ids: form.role_ids.map(Number),
      }
      return editing
        ? adminApi.updateUser(editing.id, common)
        : adminApi.createUser({ ...common, username: form.username.trim(), password: form.password })
    },
    onSuccess: (saved) => {
      refresh()
      setFormOpened(false)
      setNotice(editing ? `تغییرات «${saved.username}» ذخیره شد.` : `کاربر «${saved.username}» ساخته شد.`)
    },
  })

  const savePassword = useMutation({
    mutationFn: () => adminApi.setPassword(passwordUser!.id, password),
    onSuccess: () => {
      setNotice(`رمز عبور «${passwordUser!.username}» تغییر کرد.`)
      setPasswordUser(null)
    },
  })

  const openAdd = () => {
    save.reset()
    setEditing(null)
    setForm(EMPTY_USER)
    setFormOpened(true)
  }
  const openEdit = (user: UserRow) => {
    save.reset()
    setEditing(user)
    setForm({
      username: user.username,
      password: '',
      full_name: user.full_name ?? '',
      is_admin: user.is_admin === 'yes',
      is_active: user.is_active === 'yes',
      role_ids: user.roles.map((role) => String(role.id)),
    })
    setFormOpened(true)
  }
  const openPassword = (user: UserRow) => {
    savePassword.reset()
    setPassword('')
    setPasswordAgain('')
    setPasswordUser(user)
  }

  const users = usersQuery.data
  const filtered = useMemo(() => {
    const q = normalizeDigits(search.trim().toLowerCase())
    if (!users || !q) return users
    return users.filter((user) =>
      normalizeDigits([user.username, user.full_name ?? '', ...user.roles.map((r) => r.title)].join(' ').toLowerCase())
        .includes(q),
    )
  }, [users, search])

  const roleOptions = (rolesQuery.data ?? []).map((role) => ({ value: String(role.id), label: role.title }))

  const columns: Column<UserRow>[] = [
    {
      key: 'username', label: 'نام کاربری', render: (user) => (
        <Group gap={6} wrap="nowrap">
          <Text fw={600}><bdi dir="ltr">{user.username}</bdi></Text>
          {user.id === me?.id && <Badge size="xs" variant="light" color="gray">شما</Badge>}
        </Group>
      ),
    },
    { key: 'full_name', label: 'نام کامل', render: (user) => user.full_name ?? '—' },
    {
      key: 'roles', label: 'نقش‌ها', render: (user) => (
        <Group gap={4}>
          {user.is_admin === 'yes' && <Badge color="orange" variant="filled" radius="sm" size="sm">مدیر سیستم</Badge>}
          {user.roles.map((role) => <Badge key={role.id} variant="light" radius="sm" size="sm">{role.title}</Badge>)}
          {user.is_admin !== 'yes' && user.roles.length === 0 && <Text size="sm" c="dimmed">بدون نقش</Text>}
        </Group>
      ),
    },
    {
      key: 'status', label: 'وضعیت', render: (user) => user.is_active === 'yes'
        ? <Badge color="teal" variant="light" radius="sm">فعال</Badge>
        : <Badge color="gray" variant="light" radius="sm">غیرفعال</Badge>,
    },
    {
      key: '__actions', label: 'عملیات', render: (user) => (
        <Group gap={4} justify="center" wrap="nowrap">
          <Tooltip label="ویرایش کاربر" withArrow>
            <ActionIcon variant="subtle" color="blue" radius="md" aria-label="ویرایش کاربر" onClick={() => openEdit(user)}>
              <Pencil size={18} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="تغییر رمز عبور" withArrow>
            <ActionIcon variant="subtle" color="orange" radius="md" aria-label="تغییر رمز عبور" onClick={() => openPassword(user)}>
              <KeyRound size={18} />
            </ActionIcon>
          </Tooltip>
        </Group>
      ),
    },
  ]

  const emptyContent = (
    <Center py={64}>
      <Stack align="center" gap="xs">
        <ThemeIcon size={44} radius="xl" variant="light" color="gray"><Inbox size={24} /></ThemeIcon>
        <Text fw={600}>کاربری با این جستجو یافت نشد</Text>
        <Button variant="subtle" radius="md" onClick={() => setSearch('')}>پاک کردن جستجو</Button>
      </Stack>
    </Center>
  )

  const passwordTooShort = password.length > 0 && password.length < PASSWORD_MIN
  const passwordsDiffer = passwordAgain.length > 0 && password !== passwordAgain
  const canSubmitUser = editing != null
    || (form.username.trim() !== '' && form.password.length >= PASSWORD_MIN)

  return (
    <>
      <Paper radius="md" p="sm" withBorder shadow="xs" mb="md">
        <Group gap="sm" wrap="wrap">
          <TextInput
            radius="md"
            placeholder="جستجو در نام کاربری، نام یا نقش…"
            leftSection={<Search size={16} />}
            value={search}
            onChange={(event) => setSearch(event.currentTarget.value)}
            style={{ flex: '1 1 260px', minWidth: 200 }}
          />
          <Button
            variant="default" radius="md" leftSection={<RefreshCw size={16} />}
            onClick={refresh} loading={usersQuery.isFetching && !usersQuery.isLoading}
          >
            بروزرسانی
          </Button>
          <Button radius="md" leftSection={<UserPlus size={18} />} onClick={openAdd}>افزودن کاربر</Button>
        </Group>
      </Paper>

      {notice && (
        <Alert color="teal" radius="md" mb="md" withCloseButton onClose={() => setNotice(null)}>{notice}</Alert>
      )}

      <DataTable
        columns={columns}
        data={filtered}
        isLoading={usersQuery.isLoading}
        error={usersQuery.error}
        getRowKey={(user) => user.id}
        emptyContent={emptyContent}
      />

      <Modal
        opened={formOpened}
        onClose={() => setFormOpened(false)}
        title={editing ? `ویرایش کاربر «${editing.username}»` : 'افزودن کاربر'}
        radius="lg"
        centered
      >
        <Stack gap="sm" dir="rtl">
          <TextInput
            label="نام کاربری"
            description={editing ? 'نام کاربری بعد از ساخت تغییر نمی‌کند.' : 'حروف انگلیسی، عدد و . _ @ -'}
            required={!editing}
            disabled={editing != null}
            dir="ltr"
            autoComplete="off"
            value={form.username}
            onChange={(event) => setForm({ ...form, username: event.currentTarget.value })}
          />
          {!editing && (
            <PasswordInput
              label="رمز عبور"
              description="دست‌کم ۸ نویسه"
              required
              autoComplete="new-password"
              value={form.password}
              onChange={(event) => setForm({ ...form, password: event.currentTarget.value })}
            />
          )}
          <TextInput
            label="نام کامل"
            value={form.full_name}
            onChange={(event) => setForm({ ...form, full_name: event.currentTarget.value })}
          />
          <MultiSelect
            label="نقش‌ها"
            placeholder={roleOptions.length ? 'انتخاب نقش' : undefined}
            description={roleOptions.length === 0 ? 'هنوز نقشی نیست؛ ابتدا در زبانه «نقش‌ها» نقش بسازید.' : undefined}
            data={roleOptions}
            value={form.role_ids}
            onChange={(role_ids) => setForm({ ...form, role_ids })}
            searchable
            clearable
            nothingFoundMessage="نقشی یافت نشد"
          />
          <Switch
            label="مدیر سیستم"
            description="دسترسی کامل به همه بخش‌ها، از جمله مدیریت کاربران"
            checked={form.is_admin}
            disabled={editingSelf}
            onChange={(event) => setForm({ ...form, is_admin: event.currentTarget.checked })}
          />
          <Switch
            label="حساب فعال"
            description="کاربر غیرفعال نمی‌تواند وارد شود و درخواست‌های بعدی‌اش رد می‌شود"
            checked={form.is_active}
            disabled={editingSelf}
            onChange={(event) => setForm({ ...form, is_active: event.currentTarget.checked })}
          />
          {editingSelf && (
            <Text size="xs" c="dimmed">
              برای جلوگیری از قفل شدن سامانه، مدیر بودن و فعال بودن حساب خودتان را نمی‌توانید تغییر دهید.
            </Text>
          )}
          {save.isError && <Alert color="red" radius="md">{errorMessage(save.error, 'ذخیره کاربر انجام نشد.')}</Alert>}
          <Group justify="flex-start" gap="sm" mt="xs">
            <Button radius="md" loading={save.isPending} disabled={!canSubmitUser} onClick={() => save.mutate()}>
              ذخیره
            </Button>
            <Button variant="default" radius="md" onClick={() => setFormOpened(false)}>لغو</Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={passwordUser != null}
        onClose={() => setPasswordUser(null)}
        title={passwordUser ? `تغییر رمز عبور «${passwordUser.username}»` : ''}
        radius="lg"
        centered
      >
        <Stack gap="sm" dir="rtl">
          <PasswordInput
            label="رمز عبور جدید"
            description="دست‌کم ۸ نویسه"
            autoComplete="new-password"
            value={password}
            error={passwordTooShort ? 'رمز عبور باید دست‌کم ۸ نویسه باشد' : undefined}
            onChange={(event) => setPassword(event.currentTarget.value)}
          />
          <PasswordInput
            label="تکرار رمز عبور جدید"
            autoComplete="new-password"
            value={passwordAgain}
            error={passwordsDiffer ? 'دو رمز عبور یکسان نیستند' : undefined}
            onChange={(event) => setPasswordAgain(event.currentTarget.value)}
          />
          {savePassword.isError && (
            <Alert color="red" radius="md">{errorMessage(savePassword.error, 'تغییر رمز عبور انجام نشد.')}</Alert>
          )}
          <Group justify="flex-start" gap="sm" mt="xs">
            <Button
              radius="md"
              loading={savePassword.isPending}
              disabled={password.length < PASSWORD_MIN || password !== passwordAgain}
              onClick={() => savePassword.mutate()}
            >
              ذخیره رمز جدید
            </Button>
            <Button variant="default" radius="md" onClick={() => setPasswordUser(null)}>لغو</Button>
          </Group>
        </Stack>
      </Modal>
    </>
  )
}
