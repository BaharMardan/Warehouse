// /**
//  * Top-level application modules — the "squares" on the home page (Odoo-style
//  * app launcher) and the entries in the sidebar.
//  *
//  * This is the single source of truth: adding a new module here makes it appear
//  * on the home page AND in the navbar automatically. No other file needs to
//  * change except App.tsx (to register the route).
//  */
// import type { ComponentType, CSSProperties } from 'react'
// import type { CrudConfig } from './components/CrudResource'
// import { resources } from './resources'
// import {
//   IconDatabase, IconClipboardList, IconReceipt, IconInvoice, IconKartabl,
// } from './components/icons'

// type IconComponent = ComponentType<{ size?: number; stroke?: number }>

// export interface AppModule {
//   key: string
//   title: string           // tile caption, e.g. 'تالی'
//   description: string     // one-line hint under the caption
//   route: string           // where the tile navigates, e.g. '/tally'
//   icon: IconComponent
//   color: string           // Mantine color name, drives the tile badge
//   enabled?: boolean       // false => tile is visible but greyed out with a "به‌زودی" badge
// }

// export const modules: AppModule[] = [
//   {
//     key: 'kartabl',
//     title: 'کارتابل',
//     description: 'پیگیری پرونده‌ها از تالی تا صورتحساب',
//     route: '/kartabl',
//     icon: IconKartabl,
//     color: 'pink',
//   },
//   {
//     key: 'base-data',
//     title: 'اطلاعات پایه',
//     description: 'کالاها، نرخ‌ها، انبارها و طرف‌حساب‌ها',
//     route: '/base-data',
//     icon: IconDatabase,
//     color: 'violet',
//   },
//   {
//     key: 'tally',
//     title: 'تالی',
//     description: 'ثبت و پیگیری تالی‌های ورود کالا',
//     route: '/tally',
//     icon: IconClipboardList,
//     color: 'blue',
//   },
//   {
//     key: 'ghabz',
//     title: 'قبض انبار',
//     description: 'صدور و مشاهده قبض‌های انبار',
//     route: '/ghabz',
//     icon: IconReceipt,
//     color: 'teal',
//   },
//   {
//     key: 'invoice',
//     title: 'صورتحساب',
//     description: 'محاسبه و صدور صورتحساب',
//     route: '/invoice',
//     icon: IconInvoice,
//     // color: 'orange',
//     color: 'red',
//     enabled: false,
//   },
// ]

// /**
//  * Which module a URL belongs to. Drives the accent colour of PageHeader and the
//  * canvas tint, so every screen carries the colour of the tile it was opened from.
//  * Returns undefined on the launcher itself, which paints its own background.
//  */
// export function moduleForPath(pathname: string): AppModule | undefined {
//   if (pathname === '/') return undefined
//   // every simple-CRUD screen belongs to اطلاعات پایه
//   if (resources.some((r) => r.route === pathname)) {
//     return modules.find((m) => m.key === 'base-data')
//   }
//   return modules.find((m) => pathname === m.route || pathname.startsWith(`${m.route}/`))
// }

// /**
//  * Publishes the module accent as CSS custom properties. AppLayout sets these on
//  * `.app-canvas`, so every descendant (page header, tables, toolbars) recolours
//  * itself as the user moves between modules — no prop drilling, one definition.
//  *
//  * The `-light` / `-filled` forms are Mantine's own colour-scheme-aware tokens,
//  * so they stay correct in dark mode without a second rule.
//  */
// export function accentVars(color: string | undefined): CSSProperties {
//   if (!color) return {} as CSSProperties
//   return {
//     '--app-accent-5': `var(--mantine-color-${color}-5)`,
//     '--app-accent-6': `var(--mantine-color-${color}-6)`,
//     '--app-accent-8': `var(--mantine-color-${color}-8)`,
//     '--app-accent-light': `var(--mantine-color-${color}-light)`,
//     '--app-accent-light-hover': `var(--mantine-color-${color}-light-hover)`,
//     '--app-accent-light-color': `var(--mantine-color-${color}-light-color)`,
//     '--app-accent-filled': `var(--mantine-color-${color}-filled)`,
//   } as CSSProperties
// }

// /**
//  * How the base-data CRUD screens are grouped on /base-data.
//  * Routes are matched against `resources`; anything not listed here falls into
//  * a trailing "سایر" group so a newly added resource is never silently hidden.
//  */
// const BASE_DATA_GROUPS: { title: string; routes: string[] }[] = [
//   {
//     title: 'کالا و نرخ',
//     routes: [
//       '/kala', '/kala-price', '/kala-diamound', '/kala-other-service',
//       '/kala-strip', '/kala-time-stop', '/kala-vehicle-enter',
//     ],
//   },
//   {
//     title: 'انبار و طرف‌حساب',
//     routes: ['/anbar', '/tagh', '/owners', '/transport-companies', '/company-representatives'],
//   },
//   {
//     title: 'اطلاعات عمومی',
//     routes: ['/borders', '/countries', '/packaging-types'],
//   },
// ]

// export interface BaseDataGroup {
//   title: string
//   items: CrudConfig<any>[]
// }

// export function getBaseDataGroups(): BaseDataGroup[] {
//   const byRoute = new Map(resources.map((r) => [r.route, r]))
//   const used = new Set<string>()

//   const groups: BaseDataGroup[] = BASE_DATA_GROUPS.map((g) => {
//     const items = g.routes
//       .map((route) => {
//         const r = byRoute.get(route)
//         if (r) used.add(route)
//         return r
//       })
//       .filter((r): r is CrudConfig<any> => !!r)
//     return { title: g.title, items }
//   }).filter((g) => g.items.length > 0)

//   const leftovers = resources.filter((r) => !used.has(r.route))
//   if (leftovers.length) groups.push({ title: 'سایر', items: leftovers })

//   return groups
// }

/**
 * Top-level application modules — the "squares" on the home page (Odoo-style
 * app launcher) and the entries in the sidebar.
 *
 * This is the single source of truth: adding a new module here makes it appear
 * on the home page AND in the navbar automatically. No other file needs to
 * change except App.tsx (to register the route).
 */
import { useMemo, type ComponentType, type CSSProperties } from 'react'
import { Cog } from 'lucide-react'
import type { CrudConfig } from './components/CrudResource'
import { resources } from './resources'
import {
  IconDatabase, IconClipboardList, IconReceipt, IconInvoice, IconKartabl, IconUsers,
} from './components/icons'
import { usePermissions } from './auth/usePermissions'
import type { PermissionCode } from './auth/permissions'

type IconComponent = ComponentType<{ size?: number; stroke?: number }>

/** Rounded cog, visually closer to the familiar iOS settings symbol. */
const IconSettingsIOS: IconComponent = ({ size = 20, stroke = 1.8 }) => (
  <Cog size={size} strokeWidth={stroke} />
)

export interface AppModule {
  key: string
  title: string           // tile caption, e.g. 'تالی'
  description: string     // one-line hint under the caption
  route: string           // where the tile navigates, e.g. '/tally'
  icon: IconComponent
  color: string           // Mantine color name, drives the tile badge
  enabled?: boolean       // false => tile is visible but greyed out with a "به‌زودی" badge
  permission?: PermissionCode // shown only to users holding it; omit for every logged-in user
  adminOnly?: boolean         // shown only to admins (FA_USERS.IS_ADMIN); no permission code grants it
}

export const modules: AppModule[] = [
  {
    key: 'abandoned',
    title: 'متروکه',
    description: 'کالاهای متروکه و هشدار نزدیک‌شدن به ۹۰ روز',
    route: '/abandoned',
    icon: IconReceipt,
    color: 'yellow',
    permission: 'abandoned.view',
  },
  {
    key: 'kartabl',
    title: 'کارتابل',
    description: 'پیگیری پرونده‌ها از تالی تا صورتحساب',
    route: '/kartabl',
    icon: IconKartabl,
    color: 'pink',
    permission: 'kartabl.view',
  },
  {
    key: 'base-data',
    title: 'اطلاعات پایه',
    description: 'کالاها، نرخ‌ها، انبارها و طرف‌حساب‌ها',
    route: '/base-data',
    icon: IconDatabase,
    color: 'violet',
  },
  {
    key: 'tally',
    title: 'تالی',
    description: 'ثبت و پیگیری تالی‌های ورود کالا',
    route: '/tally',
    icon: IconClipboardList,
    color: 'blue',
    permission: 'tally.view',
  },
  {
    key: 'ghabz',
    title: 'قبض انبار',
    description: 'صدور و مشاهده قبض‌های انبار',
    route: '/ghabz',
    icon: IconReceipt,
    color: 'teal',
    permission: 'ghabz.view',
  },
  {
    key: 'invoice',
    title: 'صورتحساب',
    description: 'محاسبه و صدور صورتحساب',
    route: '/invoice',
    icon: IconInvoice,
    // color: 'orange',
    color: 'red',
    permission: 'invoice.view',
  },
  {
    key: 'users',
    title: 'مدیریت کاربران',
    description: 'کاربران، نقش‌ها و دسترسی‌ها',
    route: '/users',
    icon: IconUsers,
    color: 'orange',
    adminOnly: true,
  },
  {
    key: 'settings',
    title: 'تنظیمات',
    description: 'نرخ‌ها و مقادیر ثابت سامانه',
    route: '/settings',
    icon: IconSettingsIOS,
    color: 'gray',
    permission: 'settings.manage',
  },
]

/** The modules this user may open: the home-page tiles and the sidebar entries. */
// export function useVisibleModules(): AppModule[] {
//   const { can, isAdmin } = usePermissions()
//   return useMemo(
//     () => modules.filter((m) => (!m.adminOnly || isAdmin) && (!m.permission || can(m.permission))),
//     [can, isAdmin],
//   )
// }
/** نمایش ماژول‌ها بر اساس دسترسی‌های تعیین‌شده توسط ادمین */
export function useVisibleModules(): AppModule[] {
  const { can, isAdmin } = usePermissions()

  return useMemo(
    () =>
      modules.filter((module) => {
        if (module.adminOnly && !isAdmin) {
          return false
        }

        if (module.key === 'base-data') {
          return (
            can('base_data.edit') ||
            can('commodity.manage')
          )
        }

        if (module.permission) {
          return can(module.permission)
        }

        return true
      }),
    [can, isAdmin],
  )
}


/**
 * Which module a URL belongs to. Drives the accent colour of PageHeader and the
 * canvas tint, so every screen carries the colour of the tile it was opened from.
 * Returns undefined on the launcher itself, which paints its own background.
 */
export function moduleForPath(pathname: string): AppModule | undefined {
  if (pathname === '/') return undefined
  // every simple-CRUD screen belongs to اطلاعات پایه
  if (resources.some((r) => r.route === pathname)) {
    return modules.find((m) => m.key === 'base-data')
  }
  return modules.find((m) => pathname === m.route || pathname.startsWith(`${m.route}/`))
}

/**
 * Publishes the module accent as CSS custom properties. AppLayout sets these on
 * `.app-canvas`, so every descendant (page header, tables, toolbars) recolours
 * itself as the user moves between modules — no prop drilling, one definition.
 *
 * The `-light` / `-filled` forms are Mantine's own colour-scheme-aware tokens,
 * so they stay correct in dark mode without a second rule.
 */
export function accentVars(color: string | undefined): CSSProperties {
  if (!color) return {} as CSSProperties
  return {
    '--app-accent-5': `var(--mantine-color-${color}-5)`,
    '--app-accent-6': `var(--mantine-color-${color}-6)`,
    '--app-accent-8': `var(--mantine-color-${color}-8)`,
    '--app-accent-light': `var(--mantine-color-${color}-light)`,
    '--app-accent-light-hover': `var(--mantine-color-${color}-light-hover)`,
    '--app-accent-light-color': `var(--mantine-color-${color}-light-color)`,
    '--app-accent-filled': `var(--mantine-color-${color}-filled)`,
  } as CSSProperties
}

/**
 * How the base-data CRUD screens are grouped on /base-data.
 * Routes are matched against `resources`; anything not listed here falls into
 * a trailing "سایر" group so a newly added resource is never silently hidden.
 */
const BASE_DATA_GROUPS: { title: string; routes: string[] }[] = [
  {
    title: 'کالا و نرخ',
    routes: [
      '/kala', '/kala-price', '/kala-diamound', '/kala-other-service',
      '/kala-strip', '/kala-time-stop', '/kala-vehicle-enter',
    ],
  },
  {
    title: 'انبار و طرف‌حساب',
    routes: ['/anbar', '/tagh', '/owners', '/transport-companies', '/company-representatives'],
  },
  {
    title: 'اطلاعات عمومی',
    routes: ['/borders', '/countries', '/packaging-types', '/carrier-types', '/insurance-companies'],
  },
]

export interface BaseDataGroup {
  title: string
  items: CrudConfig<any>[]
}

export function getBaseDataGroups(): BaseDataGroup[] {
  const byRoute = new Map(resources.map((r) => [r.route, r]))
  const used = new Set<string>()

  const groups: BaseDataGroup[] = BASE_DATA_GROUPS.map((g) => {
    const items = g.routes
      .map((route) => {
        const r = byRoute.get(route)
        if (r) used.add(route)
        return r
      })
      .filter((r): r is CrudConfig<any> => !!r)
    return { title: g.title, items }
  }).filter((g) => g.items.length > 0)

  const leftovers = resources.filter((r) => !used.has(r.route))
  if (leftovers.length) groups.push({ title: 'سایر', items: leftovers })

  return groups
}
