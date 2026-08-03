import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useDebouncedValue } from '@mantine/hooks'
import {
  ActionIcon, Alert, Badge, Box, Button, Center, Divider, Grid, Group, Modal,
  Paper, SegmentedControl, Stack, Text, TextInput, ThemeIcon, Title, Tooltip,
} from '@mantine/core'
import {
  Building2, CircleAlert, Inbox, Pencil, Plus, RefreshCw, Search, Trash2,
  UserRound, UsersRound,
} from 'lucide-react'

import { apiGet, apiSend } from '../api/client'
import { DataTable, type Column } from '../components/DataTable'


type OwnerType = 'حقیقی' | 'حقوقی'

interface OwnerRepresentative {
  id_owner_representative?: number
  id_owner?: number
  name: string
  family: string
  national_code: string
  mobile: string
}

interface Owner {
  id_owner: number
  type: OwnerType
  name: string | null
  family: string | null
  national_code: string | null
  company_name: string | null
  address: string | null
  phone: string | null
  national_id: string | null
  economic_code: string | null
  representatives: OwnerRepresentative[]
}

interface OwnerFormState {
  type: OwnerType
  name: string
  family: string
  national_code: string
  company_name: string
  address: string
  phone: string
  national_id: string
  economic_code: string
  representatives: OwnerRepresentative[]
}

const emptyRepresentative = (): OwnerRepresentative => ({
  name: '', family: '', national_code: '', mobile: '',
})

const emptyOwner = (): OwnerFormState => ({
  type: 'حقیقی',
  name: '', family: '', national_code: '', company_name: '',
  address: '', phone: '', national_id: '', economic_code: '',
  representatives: [],
})

const ownerToForm = (owner: Owner): OwnerFormState => ({
  type: owner.type,
  name: owner.name ?? '',
  family: owner.family ?? '',
  national_code: owner.national_code ?? '',
  company_name: owner.company_name ?? '',
  address: owner.address ?? '',
  phone: owner.phone ?? '',
  national_id: owner.national_id ?? '',
  economic_code: owner.economic_code ?? '',
  representatives: owner.type === 'حقوقی'
    ? owner.representatives.map((representative) => ({ ...representative }))
    : [],
})

const normalizeDigits = (value: string) =>
  value.replace(/[\u06F0-\u06F9]/g, (digit) => String(digit.charCodeAt(0) - 0x06f0))
    .replace(/[\u0660-\u0669]/g, (digit) => String(digit.charCodeAt(0) - 0x0660))

const ownerTitle = (owner: Owner) => owner.type === 'حقوقی'
  ? owner.company_name ?? '—'
  : `${owner.name ?? ''} ${owner.family ?? ''}`.trim() || '—'


export function OwnersPage() {
  const queryClient = useQueryClient()
  const [opened, setOpened] = useState(false)
  const [editing, setEditing] = useState<Owner | null>(null)
  const [form, setForm] = useState<OwnerFormState>(emptyOwner)
  const [search, setSearch] = useState('')
  const [debouncedSearch] = useDebouncedValue(search, 200)

  const ownersQuery = useQuery({
    queryKey: ['owners'],
    queryFn: () => apiGet<Owner[]>('/owners'),
  })

  const refreshOwners = () => {
    queryClient.invalidateQueries({ queryKey: ['owners'] })
    queryClient.invalidateQueries({ queryKey: ['refselect', '/owners'] })
  }

  const saveOwner = useMutation({
    mutationFn: (payload: OwnerFormState) => editing
      ? apiSend<Owner>(`/owners/${editing.id_owner}`, 'PUT', payload)
      : apiSend<Owner>('/owners', 'POST', payload),
    onSuccess: () => {
      refreshOwners()
      setOpened(false)
    },
  })

  const removeOwner = useMutation({
    mutationFn: (ownerId: number) => apiSend<void>(`/owners/${ownerId}`, 'DELETE'),
    onSuccess: refreshOwners,
  })

  const openAdd = () => {
    saveOwner.reset()
    setEditing(null)
    setForm(emptyOwner())
    setOpened(true)
  }

  const openEdit = (owner: Owner) => {
    saveOwner.reset()
    setEditing(owner)
    setForm(ownerToForm(owner))
    setOpened(true)
  }

  const closeForm = () => {
    saveOwner.reset()
    setOpened(false)
  }

  const setField = <K extends keyof OwnerFormState>(key: K, value: OwnerFormState[K]) => {
    setForm((current) => ({ ...current, [key]: value }))
  }

  const setOwnerType = (type: OwnerType) => {
    setForm((current) => ({
      ...current,
      type,
      representatives: type === 'حقوقی' ? current.representatives : [],
    }))
  }

  const updateRepresentative = (
    index: number,
    key: keyof Pick<OwnerRepresentative, 'name' | 'family' | 'national_code' | 'mobile'>,
    value: string,
  ) => {
    setForm((current) => ({
      ...current,
      representatives: current.representatives.map((representative, rowIndex) =>
        rowIndex === index ? { ...representative, [key]: value } : representative,
      ),
    }))
  }

  const addRepresentative = () => {
    setForm((current) => ({
      ...current,
      representatives: [...current.representatives, emptyRepresentative()],
    }))
  }

  const removeRepresentative = (index: number) => {
    setForm((current) => ({
      ...current,
      representatives: current.representatives.filter((_, rowIndex) => rowIndex !== index),
    }))
  }

  const formError = useMemo(() => {
    if (form.type === 'حقوقی') {
      const nationalCodes = form.representatives
        .map((row) => row.national_code.trim())
        .filter(Boolean)
      if (new Set(nationalCodes).size !== nationalCodes.length) {
        return 'کد ملی نمایندگان یک صاحب کالا نباید تکراری باشد.'
      }
    }
    return null
  }, [form])

  const submit = () => {
    if (formError) return
    const clean = (value: string) => value.trim()
    saveOwner.mutate({
      ...form,
      name: form.type === 'حقیقی' ? clean(form.name) : '',
      family: form.type === 'حقیقی' ? clean(form.family) : '',
      national_code: form.type === 'حقیقی' ? clean(form.national_code) : '',
      company_name: form.type === 'حقوقی' ? clean(form.company_name) : '',
      national_id: form.type === 'حقوقی' ? clean(form.national_id) : '',
      economic_code: form.type === 'حقوقی' ? clean(form.economic_code) : '',
      address: clean(form.address),
      phone: clean(form.phone),
      representatives: form.type === 'حقوقی'
        ? form.representatives
          .map((representative) => ({
              ...representative,
              name: clean(representative.name),
              family: clean(representative.family),
              national_code: clean(representative.national_code),
              mobile: clean(representative.mobile),
            }))
          .filter((representative) =>
            Boolean(
              representative.name
              || representative.family
              || representative.national_code
              || representative.mobile,
            ),
          )
        : [],
    })
  }

  const filteredOwners = useMemo(() => {
    const query = normalizeDigits(debouncedSearch.trim().toLowerCase())
    if (!query) return ownersQuery.data ?? []
    return (ownersQuery.data ?? []).filter((owner) => {
      const representativeText = owner.representatives
        .map((representative) =>
          `${representative.name} ${representative.family} ${representative.national_code} ${representative.mobile}`,
        )
        .join(' ')
      const haystack = [
        ownerTitle(owner), owner.type, owner.national_code, owner.national_id,
        owner.economic_code, owner.phone, owner.address, representativeText,
      ].join(' ').toLowerCase()
      return normalizeDigits(haystack).includes(query)
    })
  }, [debouncedSearch, ownersQuery.data])

  const columns: Column<Owner>[] = [
    {
      key: 'type', label: 'نوع', render: (owner) => (
        <Badge
          variant="light"
          color={owner.type === 'حقوقی' ? 'indigo' : 'teal'}
          leftSection={owner.type === 'حقوقی' ? <Building2 size={13} /> : <UserRound size={13} />}
        >
          {owner.type}
        </Badge>
      ),
    },
    { key: 'owner', label: 'نام صاحب کالا', render: ownerTitle },
    {
      key: 'identifier', label: 'کد ملی / شناسه ملی',
      render: (owner) => owner.type === 'حقوقی' ? owner.national_id ?? '—' : owner.national_code ?? '—',
    },
    { key: 'phone', label: 'تلفن', field: 'phone' },
    {
      key: 'representatives', label: 'نمایندگان صاحب کالا', render: (owner) => owner.type === 'حقوقی' ? (
        <Group gap={6} wrap="nowrap">
          <UsersRound size={16} />
          <Text size="sm">{owner.representatives.length.toLocaleString('fa-IR')} نفر</Text>
        </Group>
      ) : <Text c="dimmed">—</Text>,
    },
    {
      key: '__actions', label: 'عملیات', render: (owner) => (
        <Group gap={4} justify="center" wrap="nowrap">
          <Tooltip label="ویرایش صاحب کالا و نمایندگان" withArrow>
            <ActionIcon variant="subtle" color="blue" radius="md" onClick={() => openEdit(owner)}>
              <Pencil size={18} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="حذف" withArrow>
            <ActionIcon
              variant="subtle" color="red" radius="md"
              loading={removeOwner.isPending}
              onClick={() => confirm(`حذف «${ownerTitle(owner)}» و نمایندگان آن؟`)
                && removeOwner.mutate(owner.id_owner)}
            >
              <Trash2 size={18} />
            </ActionIcon>
          </Tooltip>
        </Group>
      ),
    },
  ]

  const emptyContent = (ownersQuery.data?.length ?? 0) === 0 ? (
    <Center py={64}>
      <Stack align="center" gap="sm" ta="center" maw={380}>
        <ThemeIcon size={64} radius="xl" variant="light" color="blue"><Inbox size={34} /></ThemeIcon>
        <Text fw={600} size="lg">هنوز صاحب کالایی ثبت نشده است</Text>
        <Text size="sm" c="dimmed">صاحب حقیقی یا حقوقی را با هر مقدار اطلاعاتی که در دسترس است ثبت کنید.</Text>
        <Button mt="xs" radius="md" leftSection={<Plus size={18} />} onClick={openAdd}>
          افزودن صاحب کالا
        </Button>
      </Stack>
    </Center>
  ) : (
    <Center py={64}>
      <Stack align="center" gap="xs">
        <ThemeIcon size={44} radius="xl" variant="light" color="gray"><Search size={24} /></ThemeIcon>
        <Text fw={600}>نتیجه‌ای یافت نشد</Text>
        <Button variant="subtle" onClick={() => setSearch('')}>پاک کردن جستجو</Button>
      </Stack>
    </Center>
  )

  return (
    <Box dir="rtl" style={{ maxWidth: 1280, margin: '0 auto' }}>
      <Group justify="space-between" align="flex-end" mb="lg" wrap="wrap" gap="sm">
        <div>
          <Title order={2} fw={700}>صاحبین کالا</Title>
          <Text c="dimmed" size="sm" mt={4}>
            مدیریت اشخاص حقیقی و شرکت‌های صاحب کالا به همراه نمایندگان شرکت‌ها
          </Text>
        </div>
        <Button radius="md" leftSection={<Plus size={18} />} onClick={openAdd}>
          افزودن صاحب کالا
        </Button>
      </Group>

      <Paper radius="md" p="sm" withBorder shadow="xs" mb="md">
        <Group gap="sm" wrap="wrap" align="center">
          <TextInput
            radius="md" placeholder="جستجو در صاحبین و نمایندگان…"
            leftSection={<Search size={16} />}
            value={search} onChange={(event) => setSearch(event.currentTarget.value)}
            style={{ flex: '1 1 280px', minWidth: 220 }}
          />
          <Button
            variant="default" radius="md" leftSection={<RefreshCw size={16} />}
            onClick={refreshOwners} loading={ownersQuery.isFetching && !ownersQuery.isLoading}
          >
            بروزرسانی
          </Button>
        </Group>
      </Paper>

      {(removeOwner.isError) && (
        <Alert color="red" icon={<CircleAlert size={18} />} mb="md">
          حذف انجام نشد؛ ممکن است این صاحب کالا در تالی یا قبض انبار استفاده شده باشد.
        </Alert>
      )}

      <DataTable
        columns={columns}
        data={ownersQuery.isLoading ? undefined : filteredOwners}
        isLoading={ownersQuery.isLoading}
        error={ownersQuery.error}
        getRowKey={(owner) => owner.id_owner}
        emptyContent={emptyContent}
        minWidth={980}
      />

      {(ownersQuery.data?.length ?? 0) > 0 && (
        <Text size="xs" c="dimmed" mt="sm" ta="center">
          نمایش {filteredOwners.length.toLocaleString('fa-IR')} از {(ownersQuery.data?.length ?? 0).toLocaleString('fa-IR')} مورد
        </Text>
      )}

      <Modal
        opened={opened}
        onClose={closeForm}
        title={editing ? `ویرایش ${ownerTitle(editing)}` : 'افزودن صاحب کالا'}
        size="xl"
        centered
        radius="lg"
        overlayProps={{ backgroundOpacity: 0.55, blur: 2 }}
        styles={{
          title: { fontWeight: 700 },
          body: { maxHeight: 'calc(100dvh - 130px)', overflowY: 'auto' },
        }}
      >
        <Stack gap="lg" dir="rtl">
          <Paper withBorder radius="md" p="md">
            <Group gap="sm" mb="md">
              <ThemeIcon variant="light" size="lg" radius="md">
                {form.type === 'حقوقی' ? <Building2 size={20} /> : <UserRound size={20} />}
              </ThemeIcon>
              <div>
                <Text fw={700}>نوع صاحب کالا</Text>
                <Text size="xs" c="dimmed">فیلدهای فرم بر اساس نوع انتخاب‌شده تنظیم می‌شوند.</Text>
              </div>
            </Group>
            <SegmentedControl
              fullWidth
              value={form.type}
              onChange={(value) => setOwnerType(value as OwnerType)}
              data={[
                { value: 'حقیقی', label: 'شخص حقیقی' },
                { value: 'حقوقی', label: 'شخص حقوقی / شرکت' },
              ]}
            />
          </Paper>

          <Paper withBorder radius="md" p="md">
            <Group gap="sm" mb="md">
              <ThemeIcon variant="light" color={form.type === 'حقوقی' ? 'indigo' : 'teal'} size="lg" radius="md">
                {form.type === 'حقوقی' ? <Building2 size={20} /> : <UserRound size={20} />}
              </ThemeIcon>
              <div>
                <Text fw={700}>اطلاعات صاحب کالا</Text>
                {/* <Text size="xs" c="dimmed">تمام فیلدهای این بخش اختیاری هستند.</Text> */}
              </div>
            </Group>

            <Grid gutter="md">
              {form.type === 'حقیقی' ? (
                <>
                  <Grid.Col span={{ base: 12, sm: 6 }}>
                    <TextInput label="نام" value={form.name}
                      onChange={(event) => setField('name', event.currentTarget.value)} />
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6 }}>
                    <TextInput label="نام خانوادگی" value={form.family}
                      onChange={(event) => setField('family', event.currentTarget.value)} />
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6 }}>
                    <TextInput label="کد ملی" value={form.national_code}
                      onChange={(event) => setField('national_code', event.currentTarget.value)} />
                  </Grid.Col>
                </>
              ) : (
                <>
                  <Grid.Col span={12}>
                    <TextInput label="نام شرکت" value={form.company_name}
                      onChange={(event) => setField('company_name', event.currentTarget.value)} />
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6 }}>
                    <TextInput label="شناسه ملی" value={form.national_id}
                      onChange={(event) => setField('national_id', event.currentTarget.value)} />
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6 }}>
                    <TextInput label="کد اقتصادی" value={form.economic_code}
                      onChange={(event) => setField('economic_code', event.currentTarget.value)} />
                  </Grid.Col>
                </>
              )}
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput label="تلفن" value={form.phone}
                  onChange={(event) => setField('phone', event.currentTarget.value)} />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput label="آدرس" value={form.address}
                  onChange={(event) => setField('address', event.currentTarget.value)} />
              </Grid.Col>
            </Grid>
          </Paper>

          {form.type === 'حقوقی' && (
            <Paper withBorder radius="md" p="md">
              <Group justify="space-between" align="flex-start" mb="md" wrap="wrap" gap="sm">
                <Group gap="sm">
                  <ThemeIcon variant="light" color="violet" size="lg" radius="md">
                    <UsersRound size={20} />
                  </ThemeIcon>
                  <div>
                    <Text fw={700}>نمایندگان صاحب کالا</Text>
                    <Text size="xs" c="dimmed">
                      این افراد نماینده شرکت صاحب کالا هستند و با نمایندگان شرکت حمل‌ونقل تفاوت دارند.
                    </Text>
                  </div>
                </Group>
                <Button variant="light" color="violet" radius="md" leftSection={<Plus size={17} />}
                  onClick={addRepresentative}>
                  افزودن نماینده
                </Button>
              </Group>

              <Stack gap="md">
                {form.representatives.map((representative, index) => (
                  <Paper key={index} withBorder radius="md" p="md" bg="var(--mantine-color-gray-light)">
                    <Group justify="space-between" mb="sm">
                      <Text fw={600} size="sm">نماینده {Number(index + 1).toLocaleString('fa-IR')}</Text>
                      <Tooltip label="حذف نماینده">
                        <ActionIcon
                          variant="subtle" color="red" radius="md"
                          onClick={() => removeRepresentative(index)}
                        >
                          <Trash2 size={17} />
                        </ActionIcon>
                      </Tooltip>
                    </Group>
                    <Divider mb="md" />
                    <Grid gutter="md">
                      <Grid.Col span={{ base: 12, sm: 6 }}>
                        <TextInput label="نام" value={representative.name}
                          onChange={(event) => updateRepresentative(index, 'name', event.currentTarget.value)} />
                      </Grid.Col>
                      <Grid.Col span={{ base: 12, sm: 6 }}>
                        <TextInput label="نام خانوادگی" value={representative.family}
                          onChange={(event) => updateRepresentative(index, 'family', event.currentTarget.value)} />
                      </Grid.Col>
                      <Grid.Col span={{ base: 12, sm: 6 }}>
                        <TextInput label="کد ملی" value={representative.national_code}
                          onChange={(event) => updateRepresentative(index, 'national_code', event.currentTarget.value)} />
                      </Grid.Col>
                      <Grid.Col span={{ base: 12, sm: 6 }}>
                        <TextInput label="شماره همراه" value={representative.mobile}
                          onChange={(event) => updateRepresentative(index, 'mobile', event.currentTarget.value)} />
                      </Grid.Col>
                    </Grid>
                  </Paper>
                ))}
              </Stack>
            </Paper>
          )}

          {(formError || saveOwner.isError) && (
            <Alert color="red" icon={<CircleAlert size={18} />}>
              {saveOwner.isError ? 'ذخیره انجام نشد. اطلاعات واردشده را بررسی و دوباره تلاش کنید.' : formError}
            </Alert>
          )}

          <Group justify="flex-start" gap="sm" pos="sticky" bottom={0}
            bg="var(--mantine-color-body)" py="sm" style={{ zIndex: 1 }}>
            <Button radius="md" onClick={submit} loading={saveOwner.isPending} disabled={Boolean(formError)}>
              {editing ? 'ذخیره تغییرات' : 'ثبت صاحب کالا'}
            </Button>
            <Button variant="default" radius="md" onClick={closeForm}>لغو</Button>
          </Group>
        </Stack>
      </Modal>
    </Box>
  )
}
