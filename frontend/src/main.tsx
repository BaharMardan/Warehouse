// import React from 'react'
// import ReactDOM from 'react-dom/client'
// import { MantineProvider, DirectionProvider, createTheme } from '@mantine/core'
// import '@mantine/core/styles.css'
// import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
// import { AuthProvider } from './auth/useAuth'
// import '@mantine/core/styles.css'
// import App from './App'

// const queryClient = new QueryClient()

// const theme = createTheme({
//   fontFamily: 'Vazirmatn, sans-serif',
//   headings: { fontFamily: 'Vazirmatn, sans-serif' },
// })

// ReactDOM.createRoot(document.getElementById('root')!).render(
//   <React.StrictMode>
//     <DirectionProvider>
//       <MantineProvider theme={theme}>
//         <QueryClientProvider client={queryClient}>
//           <AuthProvider>
//             <App />
//           </AuthProvider>
//         </QueryClientProvider>
//       </MantineProvider>
//     </DirectionProvider>
//   </React.StrictMode>,
// )

import React from 'react'
import ReactDOM from 'react-dom/client'
import { MantineProvider, DirectionProvider, createTheme } from '@mantine/core'
import '@mantine/core/styles.css'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './auth/useAuth'
import { isAuthError } from './api/client'
import App from './App'

// A 401 or 403 answers the same on every retry, so fail at once and let the page
// react. Other failures keep TanStack Query's default of three retries.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: (failureCount, error) => !isAuthError(error) && failureCount < 3 },
  },
})

const theme = createTheme({
  fontFamily: 'Vazirmatn, sans-serif',
  headings: { fontFamily: 'Vazirmatn, sans-serif', fontWeight: '700' },
  primaryColor: 'blue',
  defaultRadius: 'md',
  autoContrast: true,
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <DirectionProvider>
      <MantineProvider theme={theme} defaultColorScheme="light">
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <App />
          </AuthProvider>
        </QueryClientProvider>
      </MantineProvider>
    </DirectionProvider>
  </React.StrictMode>,
)

