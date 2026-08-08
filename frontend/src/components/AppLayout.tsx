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

import { useEffect, useState, type CSSProperties } from 'react'
import {
  AppShell, NavLink, Group, Text, Button, ScrollArea, ActionIcon, Tooltip,
  UnstyledButton, useMantineColorScheme, useComputedColorScheme,
} from '@mantine/core'
import { Link, useLocation, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { resources } from '../resources'
import { modules, moduleForPath, accentVars } from '../modules'
import { IconSun, IconMoon, IconHome, IconApps } from './icons'

const navLinkStyle = { borderRadius: 8, marginBottom: 2 }

// The base-data module is the only one that expands in the sidebar; its children
// are the simple-CRUD screens registered in resources.tsx.
const isBaseDataRoute = (pathname: string) => resources.some((r) => r.route === pathname)

export function AppLayout() {
  const { signOut } = useAuth()
  const location = useLocation()
  const { setColorScheme } = useMantineColorScheme()
  const computed = useComputedColorScheme('light', { getInitialValueInEffect: true })
  const dark = computed === 'dark'

  // The sidebar behaves like a drawer: hidden by default, opened only from the
  // logo button, and closed again as soon as the user navigates somewhere. The
  // launcher tiles are the primary navigation; this is the shortcut for people
  // who already know where they are going.
  const [navOpen, setNavOpen] = useState(false)
  useEffect(() => { setNavOpen(false) }, [location.pathname])

  // Drives the canvas tint; PageHeader resolves the same module independently.
  const activeModule = moduleForPath(location.pathname)

  // Opens itself when the user lands on one of its screens (e.g. straight from
  // the launcher), but never force-closes — collapsing stays under user control.
  const [baseDataOpen, setBaseDataOpen] = useState(() => isBaseDataRoute(location.pathname))
  useEffect(() => {
    if (isBaseDataRoute(location.pathname)) setBaseDataOpen(true)
  }, [location.pathname])

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{ width: 250, breakpoint: 'sm', collapsed: { desktop: !navOpen, mobile: !navOpen } }}
      padding={0}
      styles={{ header: { boxShadow: 'var(--mantine-shadow-xs)' } }}
    >
      <style>{`
        .app-canvas {
          min-height: calc(100dvh - 60px);
          background:
            radial-gradient(120% 60% at 100% 0,
              var(--app-accent-light, transparent), transparent 65%),
            linear-gradient(180deg,
              var(--app-accent-light, transparent) 0, transparent 460px),
            var(--mantine-color-gray-0);
        }
        [data-mantine-color-scheme='dark'] .app-canvas {
          background:
            radial-gradient(120% 60% at 100% 0,
              var(--app-accent-light, transparent), transparent 65%),
            linear-gradient(180deg,
              var(--app-accent-light, transparent) 0, transparent 460px),
            var(--mantine-color-dark-8);
        }
        .app-menu-btn {
          width: 34px; height: 34px; border-radius: 10px; flex-shrink: 0;
          display: grid; place-items: center; color: #fff;
          background: linear-gradient(135deg, var(--mantine-color-blue-5), var(--mantine-color-blue-8));
          box-shadow: 0 4px 10px -4px var(--mantine-color-blue-7);
          transition: transform 120ms ease, filter 120ms ease;
        }
        .app-menu-btn:hover { transform: scale(1.06); filter: brightness(1.08); }
        .app-menu-btn:active { transform: scale(0.97); }
        .app-brand { color: inherit; text-decoration: none; min-width: 0; }

        /* Dark navigation panel — a compact echo of the launcher, with each
           module keeping the colour of its tile. Mantine's static class names
           (.mantine-NavLink-*) are a documented v7 API, so targeting them is
           stable; scoping every rule under .app-nav keeps it contained. */
        .app-nav {
          border-inline-end: none;
          background: linear-gradient(180deg, #22738f 0%, #1a5c78 55%, #12475e 100%);
        }
        [data-mantine-color-scheme='dark'] .app-nav {
          background: linear-gradient(180deg, #16506a 0%, #103e53 55%, #0a2e3e 100%);
        }
        .app-nav-heading { color: rgba(255, 255, 255, 0.6); }
        .app-nav .mantine-NavLink-root {
          color: rgba(255, 255, 255, 0.88);
          border-radius: 8px;
          margin-bottom: 2px;
        }
        .app-nav .mantine-NavLink-label { color: inherit; font-weight: 500; }
        .app-nav .mantine-NavLink-root:hover { background: rgba(255, 255, 255, 0.13); }
        .app-nav .mantine-NavLink-root[data-active] {
          background: rgba(255, 255, 255, 0.2);
          color: #fff;
        }
        .app-nav .mantine-NavLink-root[data-disabled] {
          color: rgba(255, 255, 255, 0.4);
          background: transparent;
        }
        .app-nav .mantine-NavLink-root[data-disabled] .app-nav-chip { opacity: 0.45; }
        /* children of اطلاعات پایه: plain, quieter, no chip */
        .app-nav .mantine-NavLink-children .mantine-NavLink-root {
          color: rgba(255, 255, 255, 0.72);
          font-size: var(--mantine-font-size-sm);
        }
        .app-nav-chip {
          width: 26px;
          height: 26px;
          border-radius: 8px;
          display: grid;
          place-items: center;
          color: #fff;
          flex-shrink: 0;
        }
      `}</style>

      <AppShell.Header>
        <Group h="100%" px="lg" justify="space-between" wrap="nowrap">
          <Group gap="sm" wrap="nowrap" style={{ minWidth: 0 }}>
            <Tooltip label={navOpen ? 'بستن منو' : 'باز کردن منو'} withArrow>
              <UnstyledButton
                className="app-menu-btn"
                onClick={() => setNavOpen((o) => !o)}
                aria-label="منو"
                aria-expanded={navOpen}
              >
                <IconApps size={18} />
              </UnstyledButton>
            </Tooltip>
            <Text
              component={Link} to="/" className="app-brand"
              fw={700} fz="lg" lineClamp={1}
            >
              سامانه انبار آسان تجارت فلات شرق
            </Text>
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

      <AppShell.Navbar p="sm" className="app-nav">
        <ScrollArea type="scroll" h="100%">
          <Text size="xs" fw={700} className="app-nav-heading" px="sm" mt={4} mb={8} style={{ letterSpacing: 0.5 }}>
            منوی اصلی
          </Text>

          <NavLink
            component={Link}
            to="/"
            label="خانه"
            leftSection={<span className="app-nav-chip" style={{ background: 'rgba(255,255,255,0.18)' }}><IconHome size={15} /></span>}
            active={location.pathname === '/'}
            style={navLinkStyle}
          />

          {modules.map((m) => {
            const Icon = m.icon

            if (m.enabled === false) {
              return (
                <NavLink
                  key={m.key}
                  label={m.title}
                  leftSection={<span className="app-nav-chip" style={{ background: `var(--mantine-color-${m.color}-6)` }}><Icon size={15} /></span>}
                  disabled
                  style={navLinkStyle}
                />
              )
            }

            // Expands in place instead of navigating: the drawer closes on every
            // route change, so a link here would collapse the menu the moment
            // the user tried to browse its children.
            if (m.key === 'base-data') {
              return (
                <NavLink
                  key={m.key}
                  label={m.title}
                  leftSection={<span className="app-nav-chip" style={{ background: `var(--mantine-color-${m.color}-6)` }}><Icon size={15} /></span>}
                  active={location.pathname === m.route}
                  opened={baseDataOpen}
                  onChange={setBaseDataOpen}
                  childrenOffset={14}
                  style={navLinkStyle}
                >
                  {resources.map((r) => (
                    <NavLink
                      key={r.route}
                      component={Link}
                      to={r.route}
                      label={r.title}
                      active={location.pathname === r.route}
                      style={navLinkStyle}
                    />
                  ))}
                </NavLink>
              )
            }

            return (
              <NavLink
                key={m.key}
                component={Link}
                to={m.route}
                label={m.title}
                leftSection={<span className="app-nav-chip" style={{ background: `var(--mantine-color-${m.color}-6)` }}><Icon size={15} /></span>}
                active={location.pathname.startsWith(m.route)}
                style={navLinkStyle}
              />
            )
          })}
        </ScrollArea>
      </AppShell.Navbar>

      <AppShell.Main>
        <div
          className="app-canvas"
          style={{
            padding: 'var(--mantine-spacing-lg)',
            ...accentVars(activeModule?.color),
          } as CSSProperties}
        >
          <Outlet />
        </div>
      </AppShell.Main>
    </AppShell>
  )
}