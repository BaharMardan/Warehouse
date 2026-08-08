// /**
//  * Small inline-SVG icon set. This project has no icon library, so these keep the
//  * dashboard look consistent across the generic CRUD screens and the sub-pages
//  * without adding a dependency. Each icon takes an optional size/stroke.
//  */
// import type { ReactNode } from 'react'

// type IconProps = { size?: number; stroke?: number }

// const mk = (body: ReactNode) =>
//   function Icon({ size = 20, stroke = 1.8 }: IconProps) {
//     return (
//       <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
//         strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
//         {body}
//       </svg>
//     )
//   }

// export const IconSearch = mk(<><circle cx="11" cy="11" r="7" /><path d="M21 21l-4-4" /></>)
// export const IconRefresh = mk(<><path d="M4 12a8 8 0 0 1 13.7-5.7L20 8" /><path d="M20 4v4h-4" /><path d="M20 12a8 8 0 0 1-13.7 5.7L4 16" /><path d="M4 20v-4h4" /></>)
// export const IconPlus = mk(<path d="M12 5v14M5 12h14" />)
// export const IconEdit = mk(<><path d="M4 20h4L18.5 9.5a2.1 2.1 0 0 0-3-3L5 17v3z" /><path d="M14 6l3 3" /></>)
// export const IconTrash = mk(<><path d="M4 7h16" /><path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" /><path d="M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12" /><path d="M10 11v6M14 11v6" /></>)
// export const IconEye = mk(<><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" /><circle cx="12" cy="12" r="3" /></>)
// export const IconInbox = mk(<><path d="M3 13l3-8h12l3 8" /><path d="M3 13v6h18v-6" /><path d="M3 13h5l1.5 2h5L21 13" /></>)
// export const IconAlert = mk(<><path d="M12 3l9 16H3z" /><path d="M12 10v4M12 17h.01" /></>)
// // RTL "back": chevron pointing right (toward the start of the line in an RTL layout)
// export const IconBack = mk(<path d="M9 6l6 6-6 6" />)
// export const IconUpload = mk(<><path d="M12 15V4" /><path d="M8 8l4-4 4 4" /><path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" /></>)
// export const IconSun = mk(<><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>)
// export const IconMoon = mk(<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />)

/**
 * Small inline-SVG icon set. This project has no icon library, so these keep the
 * dashboard look consistent across the generic CRUD screens and the sub-pages
 * without adding a dependency. Each icon takes an optional size/stroke.
 */
import type { ReactNode } from 'react'

type IconProps = { size?: number; stroke?: number }

const mk = (body: ReactNode) =>
  function Icon({ size = 20, stroke = 1.8 }: IconProps) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        {body}
      </svg>
    )
  }

export const IconSearch = mk(<><circle cx="11" cy="11" r="7" /><path d="M21 21l-4-4" /></>)
export const IconRefresh = mk(<><path d="M4 12a8 8 0 0 1 13.7-5.7L20 8" /><path d="M20 4v4h-4" /><path d="M20 12a8 8 0 0 1-13.7 5.7L4 16" /><path d="M4 20v-4h4" /></>)
export const IconPlus = mk(<path d="M12 5v14M5 12h14" />)
export const IconEdit = mk(<><path d="M4 20h4L18.5 9.5a2.1 2.1 0 0 0-3-3L5 17v3z" /><path d="M14 6l3 3" /></>)
export const IconTrash = mk(<><path d="M4 7h16" /><path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" /><path d="M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12" /><path d="M10 11v6M14 11v6" /></>)
export const IconEye = mk(<><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" /><circle cx="12" cy="12" r="3" /></>)
export const IconInbox = mk(<><path d="M3 13l3-8h12l3 8" /><path d="M3 13v6h18v-6" /><path d="M3 13h5l1.5 2h5L21 13" /></>)
export const IconAlert = mk(<><path d="M12 3l9 16H3z" /><path d="M12 10v4M12 17h.01" /></>)
// RTL "back": chevron pointing right (toward the start of the line in an RTL layout)
export const IconBack = mk(<path d="M9 6l6 6-6 6" />)
export const IconUpload = mk(<><path d="M12 15V4" /><path d="M8 8l4-4 4 4" /><path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" /></>)
export const IconPrint = mk(<><path d="M6 9V3h12v6" /><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" /><path d="M6 14h12v7H6z" /><path d="M18 12h.01" /></>)
export const IconSun = mk(<><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>)
export const IconMoon = mk(<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />)

// ---- module (home page) icons ----
export const IconHome = mk(<><path d="M3 10.5L12 3l9 7.5" /><path d="M5 9.5V20h14V9.5" /><path d="M10 20v-5h4v5" /></>)
export const IconApps = mk(<><rect x="3.5" y="3.5" width="7" height="7" rx="1.6" /><rect x="13.5" y="3.5" width="7" height="7" rx="1.6" /><rect x="3.5" y="13.5" width="7" height="7" rx="1.6" /><rect x="13.5" y="13.5" width="7" height="7" rx="1.6" /></>)
export const IconDatabase = mk(<><ellipse cx="12" cy="6" rx="7.5" ry="3" /><path d="M4.5 6v6c0 1.66 3.36 3 7.5 3s7.5-1.34 7.5-3V6" /><path d="M4.5 12v6c0 1.66 3.36 3 7.5 3s7.5-1.34 7.5-3v-6" /></>)
export const IconClipboardList = mk(<><path d="M9.5 4h5a1 1 0 0 1 1 1v1.5h-7V5a1 1 0 0 1 1-1z" /><path d="M8.5 6H6.5a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-2" /><path d="M8.5 11h7M8.5 15h4.5" /></>)
export const IconReceipt = mk(<><path d="M5.5 3h13v18l-2.2-1.4L14.1 21l-2.1-1.4L9.9 21l-2.2-1.4L5.5 21z" /><path d="M9 8h6M9 12h6" /></>)
export const IconInvoice = mk(<><path d="M6.5 3H14l4 4v14H6.5z" /><path d="M14 3v4h4" /><path d="M10 12h5M10 16h3.5" /></>)
