import { useState } from 'react'
import {
  Container, Paper, Title, TextInput, PasswordInput, Button, Alert, Stack,
} from '@mantine/core'
import { login } from '../api/client'
import { useAuth } from '../auth/useAuth'

export default function LoginPage() {
  const { signIn } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async () => {
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      signIn()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'خطا در ورود')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container size={420} my={80}>
      <Title order={2} ta="center" mb="lg">ورود به سامانه انبار</Title>
      <Paper withBorder shadow="sm" p="lg" radius="md">
        <Stack>
          {error && <Alert color="red">{error}</Alert>}
          <TextInput
            label="نام کاربری"
            value={username}
            onChange={(e) => setUsername(e.currentTarget.value)}
          />
          <PasswordInput
            label="رمز عبور"
            value={password}
            onChange={(e) => setPassword(e.currentTarget.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          />
          <Button onClick={handleSubmit} loading={loading} fullWidth mt="sm">
            ورود
          </Button>
        </Stack>
      </Paper>
    </Container>
  )
}