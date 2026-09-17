import { Box, Tabs } from '@mantine/core'
import { useSearchParams } from 'react-router-dom'
import { BackButton } from '../components/BackButton'
import { PageHeader } from '../components/PageHeader'
import { RolesPanel } from '../components/RolesPanel'
import { UsersPanel } from '../components/UsersPanel'

/**
 * «مدیریت کاربران»: admin-only. Users get roles; roles are sets of permissions.
 * The open tab lives in the URL (?tab=roles) so it survives a refresh.
 */
export function UserManagementPage() {
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') === 'roles' ? 'roles' : 'users'

  return (
    <Box dir="rtl" style={{ maxWidth: 1280, margin: '0 auto' }}>
      <PageHeader
        title="مدیریت کاربران"
        subtitle="کاربران سامانه، نقش‌ها و دسترسی هر نقش"
        actions={<BackButton to="/" />}
      />
      <Tabs
        value={tab}
        onChange={(value) => setParams(value === 'roles' ? { tab: 'roles' } : {}, { replace: true })}
        keepMounted={false}
      >
        <Tabs.List mb="md">
          <Tabs.Tab value="users">کاربران</Tabs.Tab>
          <Tabs.Tab value="roles">نقش‌ها</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="users"><UsersPanel /></Tabs.Panel>
        <Tabs.Panel value="roles"><RolesPanel /></Tabs.Panel>
      </Tabs>
    </Box>
  )
}

export default UserManagementPage
