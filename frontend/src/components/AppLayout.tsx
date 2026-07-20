// import { AppShell, NavLink, Group, Text, Button, ScrollArea } from '@mantine/core'
// import { Link, useLocation, Outlet } from 'react-router-dom'
// import { useAuth } from '../auth/useAuth'
// import { resources } from '../resources'

// export function AppLayout() {
//   const { signOut } = useAuth()
//   const location = useLocation()

//   return (
//     <AppShell header={{ height: 56 }} navbar={{ width: 240, breakpoint: 'sm' }} padding="md">
//       <AppShell.Header>
//         <Group h="100%" px="md" justify="space-between">
//           <Text fw={700}>سامانه انبار آسان تجارت فلات شرق</Text>
//           <Button variant="subtle" color="red" onClick={signOut}>خروج</Button>
//         </Group>
//       </AppShell.Header>

//       <AppShell.Navbar p="xs">
//         <ScrollArea>
//           {resources.map((r) => (
//             <NavLink
//               key={r.route}
//               component={Link}
//               to={r.route}
//               label={r.title}
//               active={location.pathname === r.route}
//             />
//           ))}
//         </ScrollArea>
//       </AppShell.Navbar>

//       <AppShell.Main>
//         <Outlet />
//       </AppShell.Main>
//     </AppShell>
//   )
// }

import {
  AppShell, NavLink, Group, Text, Button, ScrollArea, ActionIcon, Tooltip,
  useMantineColorScheme, useComputedColorScheme,
} from '@mantine/core'
import { Link, useLocation, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { resources } from '../resources'
import { IconSun, IconMoon } from './icons'

export function AppLayout() {
  const { signOut } = useAuth()
  const location = useLocation()
  const { setColorScheme } = useMantineColorScheme()
  const computed = useComputedColorScheme('light', { getInitialValueInEffect: true })
  const dark = computed === 'dark'

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{ width: 250, breakpoint: 'sm' }}
      padding={0}
      styles={{ header: { boxShadow: 'var(--mantine-shadow-xs)' } }}
    >
      <style>{`
        .app-canvas { background: var(--mantine-color-gray-0); min-height: calc(100dvh - 60px); }
        [data-mantine-color-scheme='dark'] .app-canvas { background: var(--mantine-color-dark-8); }
      `}</style>

      <AppShell.Header>
        <Group h="100%" px="lg" justify="space-between" wrap="nowrap">
          <Group gap="sm" wrap="nowrap">
            <div style={{
              width: 32, height: 32, borderRadius: 9, flexShrink: 0,
              background: 'linear-gradient(135deg, var(--mantine-color-blue-6), var(--mantine-color-blue-8))',
              display: 'grid', placeItems: 'center', color: 'white', fontWeight: 800, fontSize: 15,
            }}></div>
            <Text fw={700} fz="lg" lineClamp={1}>سامانه انبار آسان تجارت فلات شرق</Text>
          </Group>
          <Group gap="xs" wrap="nowrap">
            <Tooltip label={dark ? 'حالت روز' : 'حالت شب'} withArrow>
              <ActionIcon
                variant="default" size="lg" radius="md"
                onClick={() => setColorScheme(dark ? 'light' : 'dark')}
                aria-label="تغییر حالت نمایش"
              >
                {dark ? <IconSun size={18} /> : <IconMoon size={18} />}
              </ActionIcon>
            </Tooltip>
            <Button variant="subtle" color="red" radius="md" onClick={signOut}>خروج</Button>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="sm">
        <ScrollArea type="scroll" h="100%">
          <Text size="xs" fw={700} c="dimmed" px="sm" mt={4} mb={8} style={{ letterSpacing: 0.5 }}>
            منوی اصلی
          </Text>
          {resources.map((r) => (
            <NavLink
              key={r.route}
              component={Link}
              to={r.route}
              label={r.title}
              active={location.pathname === r.route}
              style={{ borderRadius: 8, marginBottom: 2 }}
            />
          ))}
        </ScrollArea>
      </AppShell.Navbar>

      <AppShell.Main>
        <div className="app-canvas" style={{ padding: 'var(--mantine-spacing-lg)' }}>
          <Outlet />
        </div>
      </AppShell.Main>
    </AppShell>
  )
}