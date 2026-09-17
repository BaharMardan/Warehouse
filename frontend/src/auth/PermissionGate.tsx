import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Button, Center, Loader, Stack, Text, ThemeIcon } from '@mantine/core'
import { ShieldX } from 'lucide-react'
import { useAuth } from './useAuth'
import { useCurrentUser, usePermissions } from './usePermissions'
import type { PermissionCode } from './permissions'

/**
 * Renders the app only after /auth/me has answered, so tiles, menu entries and
 * buttons never flash on screen before the user's permissions are known.
 */
export function CurrentUserGate({ children }: { children: ReactNode }) {
  const { signOut } = useAuth()
  const { data, isError, isFetching, refetch } = useCurrentUser()

  if (data) return <>{children}</>

  if (isError) {
    return (
      <Center h="100dvh" dir="rtl">
        <Stack align="center" gap="sm" ta="center" maw={380}>
          <Text fw={700}>دریافت اطلاعات کاربر ناموفق بود</Text>
          <Text size="sm" c="dimmed">اتصال به سرور را بررسی کنید و دوباره تلاش کنید.</Text>
          <Button radius="md" loading={isFetching} onClick={() => refetch()}>
            تلاش دوباره
          </Button>
          <Button variant="subtle" color="red" radius="md" onClick={signOut}>
            خروج
          </Button>
        </Stack>
      </Center>
    )
  }

  return (
    <Center h="100dvh">
      <Loader />
    </Center>
  )
}

/**
 * Route guard: renders the page only for users holding `code`, the same code
 * the backend enforces on that page's API calls. Anyone else gets a clear
 * message instead of a screen whose every request would fail.
 */
export function RequirePermission({ code, children }: { code: PermissionCode; children: ReactNode }) {
  const { can } = usePermissions()
  return can(code) ? <>{children}</> : <NoAccess />
}

/** Route guard for admin-only pages such as user management, which no permission code grants. */
export function RequireAdmin({ children }: { children: ReactNode }) {
  const { isAdmin } = usePermissions()
  return isAdmin ? <>{children}</> : <NoAccess />
}

function NoAccess() {
  return (
    <Center py={96} dir="rtl">
      <Stack align="center" gap="sm" ta="center" maw={420}>
        <ThemeIcon size={64} radius="xl" variant="light" color="red">
          <ShieldX size={34} />
        </ThemeIcon>
        <Text fw={700} size="lg">دسترسی به این بخش برای شما تعریف نشده است</Text>
        <Text size="sm" c="dimmed">
          اگر به این بخش نیاز دارید، از مدیر سامانه بخواهید دسترسی لازم را به نقش شما اضافه کند.
        </Text>
        <Button component={Link} to="/" variant="light" radius="md">
          بازگشت به صفحه اصلی
        </Button>
      </Stack>
    </Center>
  )
}
