import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Center, Group, Loader, NumberInput, Paper, Stack, Text, ThemeIcon } from '@mantine/core'
import { Cog, Save } from 'lucide-react'
import { apiGet, apiSend, errorMessage } from '../api/client'
import { BackButton } from '../components/BackButton'
import { PageHeader } from '../components/PageHeader'
import './SettingsPage.css'

type AppSetting = {
  key: string
  title: string
  value_number: string
  unit: string
  description: string
}

const SETTINGS_KEY = ['app-settings']

export function SettingsPage() {
  const queryClient = useQueryClient()
  const settingsQuery = useQuery({
    queryKey: SETTINGS_KEY,
    queryFn: () => apiGet<AppSetting[]>('/settings'),
  })
  const [values, setValues] = useState<Record<string, number | ''>>({})

  useEffect(() => {
    if (!settingsQuery.data) return
    setValues(Object.fromEntries(settingsQuery.data.map((item) => [item.key, Number(item.value_number)])))
  }, [settingsQuery.data])

  const save = useMutation({
    mutationFn: async () => Promise.all(
      (settingsQuery.data ?? []).map((setting) =>
        apiSend<AppSetting>(`/settings/${setting.key}`, 'PUT', {
          value_number: values[setting.key] === '' || values[setting.key] == null
            ? 0
            : values[setting.key],
        }),
      ),
    ),
    onSuccess: (saved) => queryClient.setQueryData(SETTINGS_KEY, saved),
  })

  return (
    <div dir="rtl" className="settings-page">
      <PageHeader
        title="تنظیمات سامانه"
        subtitle="مدیریت نرخ‌ها و مقادیر ثابت مورد استفاده در بخش‌های مختلف سامانه"
        actions={<BackButton to="/" />}
        color="indigo"
      />

      <Paper className="settings-panel" withBorder radius="lg" p={{ base: 'md', sm: 'lg' }}>
        <Group gap="sm" mb="lg">
          <ThemeIcon className="settings-cog" size={46} radius="md">
            <Cog size={27} strokeWidth={2.1} />
          </ThemeIcon>
          <div>
            <Text className="settings-section-title">مقادیر ثابت سامانه</Text>
            {/* <Text className="settings-section-description">نرخ‌ها در محاسبات مرتبط، از جمله صورتحساب، به‌صورت یکپارچه استفاده می‌شوند.</Text> */}
          </div>
        </Group>

        {settingsQuery.isLoading && <Center py="xl"><Loader /></Center>}
        {settingsQuery.isError && <Alert color="red">دریافت تنظیمات ناموفق بود.</Alert>}

        {settingsQuery.data && (
          <Stack gap="md">
            {settingsQuery.data.map((setting) => (
              <Paper key={setting.key} className="settings-rate-card" radius="lg" p="lg">
                <Group justify="space-between" align="flex-start" wrap="wrap" gap="md">
                  <div>
                    <Text className="settings-rate-title">{setting.title}</Text>
                    <Text className="settings-rate-description">{setting.description}</Text>
                  </div>
                  <NumberInput
                    className="settings-rate-input"
                    min={0}
                    decimalScale={4}
                    thousandSeparator=","
                    suffix={` ${setting.unit}`}
                    value={values[setting.key] ?? ''}
                    onChange={(value) => setValues((current) => ({
                      ...current,
                      [setting.key]: value === '' ? '' : Number(value),
                    }))}
                  />
                </Group>
              </Paper>
            ))}
            {save.isError && <Alert color="red">{errorMessage(save.error, 'ذخیره تنظیمات ناموفق بود.')}</Alert>}
            {save.isSuccess && <Alert color="teal">تنظیمات با موفقیت ذخیره شد.</Alert>}
            <Group className="settings-save-row" justify="space-between" mt="sm">
              <Text size="sm" c="dimmed"></Text>
              <Button className="settings-save-button" leftSection={<Save size={18} />} loading={save.isPending} onClick={() => save.mutate()}>
                ذخیره تنظیمات
              </Button>
            </Group>
          </Stack>
        )}
      </Paper>
    </div>
  )
}

export default SettingsPage
