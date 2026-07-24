// import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
// import { useAuth } from './auth/useAuth'
// import { AppLayout } from './components/AppLayout'
// import { CrudResource } from './components/CrudResource'
// import LoginPage from './pages/LoginPage'
// import { resources } from './resources'
// import { TallyHeaderForm } from './pages/TallyHeaderForm'
// import { TallyListPage } from './pages/TallyListPage'
// import { TallyDetailPage } from './pages/TallyDetailPage'
// import { GhabzListPage } from './pages/GhabzListPage'
// import { GhabzDetailPage } from './pages/GhabzDetailPage'
// import { GhabzHeaderForm } from './pages/GhabzHeaderForm'
// import { CommodityCatalogPage } from './pages/CommodityCatalogPage'

// // import ScratchTest from './pages/ScratchTest'

// export default function App() {
//   const { isAuthed } = useAuth()
//   if (!isAuthed) return <LoginPage />

//   return (
//     <BrowserRouter>
//       <Routes>
//         <Route element={<AppLayout />}>
//           {/* /kala is now the commodity catalog (FA_COMMODITY_CATALOG), not the old
//               FA_KALA CRUD grid — render the custom page instead of the generic CrudResource. */}
//           {resources.filter((r) => r.route !== '/kala').map((r) => (
//             <Route key={r.route} path={r.route} element={<CrudResource config={r} />} />
//           ))}
//           <Route path="/kala" element={<CommodityCatalogPage />} />
//           {
//           /* complex pages get added here later, e.g. <Route path="/tally" element={<TallyPage />} /> */}
//           {/* <Route path="/scratch-test" element={<ScratchTest />} /> */}
//           <Route path="*" element={<Navigate to={resources[0].route} replace />} />
//           <Route path="/tally/new" element={<TallyHeaderForm />} />
//           <Route path="/tally" element={<TallyListPage />} />
//           <Route path="/tally/:tallyNumber" element={<TallyDetailPage />} />
//           <Route path="/tally/:tallyNumber/edit" element={<TallyHeaderForm />} />
//           <Route path="/ghabz" element={<GhabzListPage />} />
//           <Route path="/ghabz/:id" element={<GhabzDetailPage />} />
//           <Route path="/ghabz/new" element={<GhabzHeaderForm />} />
//           <Route path="/ghabz/:id/edit" element={<GhabzHeaderForm />} />
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
import { GhabzHeaderForm } from './pages/GhabzHeaderForm'
import { CommodityCatalogPage } from './pages/CommodityCatalogPage'

// import ScratchTest from './pages/ScratchTest'

export default function App() {
  const { isAuthed } = useAuth()
  if (!isAuthed) return <LoginPage />

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/tally/:tallyNumber/print" element={<TallyPrintPage />} />
        <Route element={<AppLayout />}>
          {/* /kala is now the commodity catalog (FA_COMMODITY_CATALOG), not the old
              FA_KALA CRUD grid — render the custom page instead of the generic CrudResource. */}
          {resources.filter((r) => r.route !== '/kala').map((r) => (
            <Route key={r.route} path={r.route} element={<CrudResource config={r} />} />
          ))}
          <Route path="/kala" element={<CommodityCatalogPage />} />
          {
          /* complex pages get added here later, e.g. <Route path="/tally" element={<TallyPage />} /> */}
          {/* <Route path="/scratch-test" element={<ScratchTest />} /> */}
          <Route path="*" element={<Navigate to={resources[0].route} replace />} />
          <Route path="/tally/new" element={<TallyHeaderForm />} />
          <Route path="/tally" element={<TallyListPage />} />
          <Route path="/tally/:tallyNumber" element={<TallyDetailPage />} />
          <Route path="/tally/:tallyNumber/edit" element={<TallyHeaderForm />} />
          <Route path="/ghabz" element={<GhabzListPage />} />
          <Route path="/ghabz/:id" element={<GhabzDetailPage />} />
          <Route path="/ghabz/new" element={<GhabzHeaderForm />} />
          <Route path="/ghabz/:id/edit" element={<GhabzHeaderForm />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
