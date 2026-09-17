// import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
// import { useAuth } from './auth/useAuth'
// import { AppLayout } from './components/AppLayout'
// import { CrudResource } from './components/CrudResource'
// import LoginPage from './pages/LoginPage'
// import { resources } from './resources'
// import { TallyHeaderForm } from './pages/TallyHeaderForm'
// import { TallyListPage } from './pages/TallyListPage'
// import { TallyDetailPage } from './pages/TallyDetailPage'
// import { TallyPrintPage } from './pages/TallyPrintPage'
// import { GhabzListPage } from './pages/GhabzListPage'
// import { GhabzDetailPage } from './pages/GhabzDetailPage'
// import { GhabzPrintPage } from './pages/GhabzPrintPage'
// import { GhabzHeaderForm } from './pages/GhabzHeaderForm'
// import { CommodityCatalogPage } from './pages/CommodityCatalogPage'
// import { OwnersPage } from './pages/OwnersPage'
// import { HomePage } from './pages/HomePage'
// import { KartablPage } from './pages/KartablPage'
// import { BaseDataPage } from './pages/BaseDataPage'

// // import ScratchTest from './pages/ScratchTest'

// export default function App() {
//   const { isAuthed } = useAuth()
//   if (!isAuthed) return <LoginPage />

//   return (
//     <BrowserRouter>
//       <Routes>
//         <Route path="/tally/id/:tallyId/print" element={<TallyPrintPage />} />
//         <Route path="/tally/:tallyNumber/print" element={<TallyPrintPage />} />
//         <Route path="/ghabz/:id/print" element={<GhabzPrintPage />} />
//         <Route element={<AppLayout />}>
//           {/* Landing page after login: the Odoo-style module launcher. */}
//           <Route index element={<HomePage />} />
//           <Route path="/base-data" element={<BaseDataPage />} />
//           {/* /kala is now the commodity catalog (FA_COMMODITY_CATALOG), not the old
//               FA_KALA CRUD grid — render the custom page instead of the generic CrudResource. */}
//           {resources.filter((r) => !['/kala', '/owners'].includes(r.route)).map((r) => (
//             <Route key={r.route} path={r.route} element={<CrudResource config={r} />} />
//           ))}
//           <Route path="/kala" element={<CommodityCatalogPage />} />
//           <Route path="/owners" element={<OwnersPage />} />
//           {
//           /* complex pages get added here later, e.g. <Route path="/tally" element={<TallyPage />} /> */}
//           {/* <Route path="/scratch-test" element={<ScratchTest />} /> */}
//           <Route path="*" element={<Navigate to="/" replace />} />
//           <Route path="/tally/new" element={<TallyHeaderForm />} />
//           <Route path="/tally" element={<TallyListPage />} />
//           <Route path="/tally/id/:tallyId" element={<TallyDetailPage />} />
//           <Route path="/tally/id/:tallyId/edit" element={<TallyHeaderForm />} />
//           <Route path="/tally/:tallyNumber" element={<TallyDetailPage />} />
//           <Route path="/tally/:tallyNumber/edit" element={<TallyHeaderForm />} />
//           <Route path="/ghabz" element={<GhabzListPage />} />
//           <Route path="/ghabz/:id" element={<GhabzDetailPage />} />
//           <Route path="/ghabz/new" element={<GhabzHeaderForm />} />
//           <Route path="/ghabz/:id/edit" element={<GhabzHeaderForm />} />
//           <Route path="/kartabl" element={<KartablPage />} />
//         </Route>
//       </Routes>
//     </BrowserRouter>
//   )
// }


import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './auth/useAuth'
import { AppLayout } from './components/AppLayout'
import { CrudResource } from './components/CrudResource'
import LoginPage from './pages/LoginPage'
import { resources } from './resources'
import { TallyHeaderForm } from './pages/TallyHeaderForm'
import { TallyListPage } from './pages/TallyListPage'
import { TallyDetailPage } from './pages/TallyDetailPage'
import { TallyPrintPage } from './pages/TallyPrintPage'
import { GhabzListPage } from './pages/GhabzListPage'
import { GhabzDetailPage } from './pages/GhabzDetailPage'
import { GhabzPrintPage } from './pages/GhabzPrintPage'
import { GhabzHeaderForm } from './pages/GhabzHeaderForm'
import { CommodityCatalogPage } from './pages/CommodityCatalogPage'
import { OwnersPage } from './pages/OwnersPage'
import { HomePage } from './pages/HomePage'
import { KartablPage } from './pages/KartablPage'
import { BaseDataPage } from './pages/BaseDataPage'
import { InvoiceListPage } from './pages/InvoiceListPage'
import { InvoiceDetailPage } from './pages/InvoiceDetailPage'
import { InvoicePrintPage } from './pages/InvoicePrintPage'
import { CurrentUserGate, RequireAdmin, RequirePermission } from './auth/PermissionGate'
import { UserManagementPage } from './pages/UserManagementPage'

// import ScratchTest from './pages/ScratchTest'

export default function App() {
  const { isAuthed } = useAuth()
  if (!isAuthed) return <LoginPage />

  return (
    <CurrentUserGate>
      <AppRoutes />
    </CurrentUserGate>
  )
}

// Pages that need a permission are wrapped in RequirePermission with the code the
// backend enforces on their API calls. Base-data screens stay open: every logged-in
// user may read lookups, and their edit buttons check base_data.edit themselves.
function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/tally/id/:tallyId/print" element={<RequirePermission code="tally.view"><TallyPrintPage /></RequirePermission>} />
        <Route path="/tally/:tallyNumber/print" element={<RequirePermission code="tally.view"><TallyPrintPage /></RequirePermission>} />
        <Route path="/ghabz/:id/print" element={<RequirePermission code="ghabz.view"><GhabzPrintPage /></RequirePermission>} />
        <Route path="/invoice/:id/print" element={<RequirePermission code="invoice.view"><InvoicePrintPage /></RequirePermission>} />
        <Route element={<AppLayout />}>
          {/* Landing page after login: the Odoo-style module launcher. */}
          <Route index element={<HomePage />} />
          <Route path="/base-data" element={<BaseDataPage />} />
          {/* /kala is now the commodity catalog (FA_COMMODITY_CATALOG), not the old
              FA_KALA CRUD grid — render the custom page instead of the generic CrudResource. */}
          {resources.filter((r) => !['/kala', '/owners'].includes(r.route)).map((r) => (
            <Route key={r.route} path={r.route} element={<CrudResource config={r} />} />
          ))}
          <Route path="/kala" element={<CommodityCatalogPage />} />
          <Route path="/owners" element={<OwnersPage />} />
          {
          /* complex pages get added here later, e.g. <Route path="/tally" element={<TallyPage />} /> */}
          {/* <Route path="/scratch-test" element={<ScratchTest />} /> */}
          <Route path="*" element={<Navigate to="/" replace />} />
          <Route path="/tally/new" element={<RequirePermission code="tally.edit"><TallyHeaderForm /></RequirePermission>} />
          <Route path="/tally" element={<RequirePermission code="tally.view"><TallyListPage /></RequirePermission>} />
          <Route path="/tally/id/:tallyId" element={<RequirePermission code="tally.view"><TallyDetailPage /></RequirePermission>} />
          <Route path="/tally/id/:tallyId/edit" element={<RequirePermission code="tally.edit"><TallyHeaderForm /></RequirePermission>} />
          <Route path="/tally/:tallyNumber" element={<RequirePermission code="tally.view"><TallyDetailPage /></RequirePermission>} />
          <Route path="/tally/:tallyNumber/edit" element={<RequirePermission code="tally.edit"><TallyHeaderForm /></RequirePermission>} />
          <Route path="/ghabz" element={<RequirePermission code="ghabz.view"><GhabzListPage /></RequirePermission>} />
          {/* receipts are issued from the tally page now; old links must not fall through to /ghabz/:id */}
          <Route path="/ghabz/new" element={<Navigate to="/ghabz" replace />} />
          <Route path="/ghabz/:id" element={<RequirePermission code="ghabz.view"><GhabzDetailPage /></RequirePermission>} />
          <Route path="/ghabz/:id/edit" element={<RequirePermission code="ghabz.edit"><GhabzHeaderForm /></RequirePermission>} />
          <Route path="/kartabl" element={<RequirePermission code="kartabl.view"><KartablPage /></RequirePermission>} />
          <Route path="/invoice" element={<RequirePermission code="invoice.view"><InvoiceListPage /></RequirePermission>} />
          <Route path="/invoice/:id" element={<RequirePermission code="invoice.view"><InvoiceDetailPage /></RequirePermission>} />
          <Route path="/users" element={<RequireAdmin><UserManagementPage /></RequireAdmin>} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
