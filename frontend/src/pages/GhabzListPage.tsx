// import { useQuery } from '@tanstack/react-query'
// import { useNavigate } from 'react-router-dom'
// import { Title, Button, Group, Table, Paper, Loader, Center, Text } from '@mantine/core'
// import { toJalaali } from 'jalaali-js'
// import { apiGet } from '../api/client'

// type GhabzRow = {
//   id_ghabz: number
//   number_ghabz: number | null
//   number_tali: number | null
//   tali_id: number | null
//   date_unloading: string | null
//   marze_name: string | null
//   country_name: string | null
//   company_name: string | null
//   owner_name: string | null
//   anbar_name: string | null
// }

// function isoToJalali(iso: string | null): string {
//   if (!iso) return '—'
//   const [gy, gm, gd] = iso.slice(0, 10).split('-').map(Number)
//   if (!gy || !gm || !gd) return '—'
//   const { jy, jm, jd } = toJalaali(gy, gm, gd)
//   const pad = (n: number) => String(n).padStart(2, '0')
//   return `${jy}/${pad(jm)}/${pad(jd)}`
// }

// export function GhabzListPage() {
//   const navigate = useNavigate()
//   const { data, isLoading, isError } = useQuery({
//     queryKey: ['ghabz-list'],
//     queryFn: () => apiGet<GhabzRow[]>('/ghabz/list'),
//   })

//   return (
//     <div dir="rtl">
//       <Group justify="space-between" mb="md">
//         <Title order={2}>لیست قبض‌های انبار</Title>
//         <Button onClick={() => navigate('/ghabz/new')}>ایجاد قبض جدید</Button>
//       </Group>
//       <Paper shadow="xs" p="md">
//         {isLoading && <Center py="xl"><Loader /></Center>}
//         {isError && <Center py="xl"><Text c="red">خطا در بارگذاری قبض‌ها.</Text></Center>}
//         {data && data.length === 0 && (
//           <Center py="xl"><Text c="dimmed">هنوز قبضی ثبت نشده است.</Text></Center>
//         )}
//         {data && data.length > 0 && (
//           <Table striped highlightOnHover withTableBorder>
//             <Table.Thead>
//               <Table.Tr>
//                 <Table.Th>شماره قبض</Table.Th>
//                 <Table.Th>شماره تالی</Table.Th>
//                 <Table.Th>نام مرز</Table.Th>
//                 <Table.Th>کشور</Table.Th>
//                 <Table.Th>شرکت</Table.Th>
//                 <Table.Th>صاحب کالا</Table.Th>
//                 <Table.Th>انبار</Table.Th>
//                 <Table.Th>تاریخ تخلیه</Table.Th>
//               </Table.Tr>
//             </Table.Thead>
//             <Table.Tbody>
//               {data.map((row) => (
//                 <Table.Tr key={row.id_ghabz} style={{ cursor: 'pointer' }}
//                   onClick={() => navigate(`/ghabz/${row.id_ghabz}`)}>
//                   <Table.Td>{row.number_ghabz ?? '—'}</Table.Td>
//                   <Table.Td>{row.number_tali ?? '—'}</Table.Td>
//                   <Table.Td>{row.marze_name ?? '—'}</Table.Td>
//                   <Table.Td>{row.country_name ?? '—'}</Table.Td>
//                   <Table.Td>{row.company_name?.trim() || '—'}</Table.Td>
//                   <Table.Td>{row.owner_name?.trim() || '—'}</Table.Td>
//                   <Table.Td>{row.anbar_name ?? '—'}</Table.Td>
//                   <Table.Td>{isoToJalali(row.date_unloading)}</Table.Td>
//                 </Table.Tr>
//               ))}
//             </Table.Tbody>
//           </Table>
//         )}
//       </Paper>
//     </div>
//   )
// }

import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { BackButton } from '../components/BackButton'
import { PageHeader } from '../components/PageHeader'
import { Button, Table, Paper, Loader, Center, Text } from '@mantine/core'
import { toJalaali } from 'jalaali-js'
import { apiGet } from '../api/client'
import { TallyNumber } from '../components/TallyNumber'

type GhabzRow = {
  id_ghabz: number
  number_ghabz: number | null
  number_tali: string | null
  tali_id: number | null
  date_unloading: string | null
  marze_name: string | null
  country_name: string | null
  company_name: string | null
  owner_name: string | null
  anbar_name: string | null
}

function isoToJalali(iso: string | null): string {
  if (!iso) return '—'
  const [gy, gm, gd] = iso.slice(0, 10).split('-').map(Number)
  if (!gy || !gm || !gd) return '—'
  const { jy, jm, jd } = toJalaali(gy, gm, gd)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${jy}/${pad(jm)}/${pad(jd)}`
}

export function GhabzListPage() {
  const navigate = useNavigate()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['ghabz-list'],
    queryFn: () => apiGet<GhabzRow[]>('/ghabz/list'),
  })

  return (
    <div dir="rtl">
      <PageHeader
        title="لیست قبض‌های انبار"
        subtitle="مدیریت قبض‌های انبار"
        actions={
          <>
            <Button variant="white" radius="md" onClick={() => navigate('/ghabz/new')}>ایجاد قبض جدید</Button>
            <BackButton to="/" />
          </>
        }
      />
      <Paper shadow="xs" p="md">
        {isLoading && <Center py="xl"><Loader /></Center>}
        {isError && <Center py="xl"><Text c="red">خطا در بارگذاری قبض‌ها.</Text></Center>}
        {data && data.length === 0 && (
          <Center py="xl"><Text c="dimmed">هنوز قبضی ثبت نشده است.</Text></Center>
        )}
        {data && data.length > 0 && (
          <Table striped highlightOnHover withTableBorder>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>شماره قبض</Table.Th>
                <Table.Th>شماره تالی</Table.Th>
                <Table.Th>نام مرز</Table.Th>
                <Table.Th>کشور</Table.Th>
                <Table.Th>شرکت</Table.Th>
                <Table.Th>صاحب کالا</Table.Th>
                <Table.Th>انبار</Table.Th>
                <Table.Th>تاریخ تخلیه</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data.map((row) => (
                <Table.Tr key={row.id_ghabz} style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/ghabz/${row.id_ghabz}`)}>
                  <Table.Td>{row.number_ghabz ?? '—'}</Table.Td>
                  <Table.Td><TallyNumber value={row.number_tali} /></Table.Td>
                  <Table.Td>{row.marze_name ?? '—'}</Table.Td>
                  <Table.Td>{row.country_name ?? '—'}</Table.Td>
                  <Table.Td>{row.company_name?.trim() || '—'}</Table.Td>
                  <Table.Td>{row.owner_name?.trim() || '—'}</Table.Td>
                  <Table.Td>{row.anbar_name ?? '—'}</Table.Td>
                  <Table.Td>{isoToJalali(row.date_unloading)}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Paper>
    </div>
  )
}
