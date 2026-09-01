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

// import ScratchTest from './pages/ScratchTest'

export default function App() {
  const { isAuthed } = useAuth()
  if (!isAuthed) return <LoginPage />

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/tally/id/:tallyId/print" element={<TallyPrintPage />} />
        <Route path="/tally/:tallyNumber/print" element={<TallyPrintPage />} />
        <Route path="/ghabz/:id/print" element={<GhabzPrintPage />} />
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
          <Route path="/tally/new" element={<TallyHeaderForm />} />
          <Route path="/tally" element={<TallyListPage />} />
          <Route path="/tally/id/:tallyId" element={<TallyDetailPage />} />
          <Route path="/tally/id/:tallyId/edit" element={<TallyHeaderForm />} />
          <Route path="/tally/:tallyNumber" element={<TallyDetailPage />} />
          <Route path="/tally/:tallyNumber/edit" element={<TallyHeaderForm />} />
          <Route path="/ghabz" element={<GhabzListPage />} />
          <Route path="/ghabz/:id" element={<GhabzDetailPage />} />
          <Route path="/ghabz/new" element={<GhabzHeaderForm />} />
          <Route path="/ghabz/:id/edit" element={<GhabzHeaderForm />} />
          <Route path="/kartabl" element={<KartablPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
