import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Group, PasswordInput, Stack, Text } from '@mantine/core'
import { apiSend, errorMessage } from '../api/client'

export function PasswordChangeForm({ temporary = false, onSuccess, onCancel }: {
  temporary?: boolean; onSuccess?: () => void; onCancel?: () => void
}) {
  const qc = useQueryClient()
  const [current, setCurrent] = useState('')
  const [password, setPassword] = useState('')
  const [again, setAgain] = useState('')
  const change = useMutation({
    mutationFn: () => apiSend<void>('/auth/password', 'PUT', { current_password: current, new_password: password }),
    onSuccess: async () => {
      setCurrent(''); setPassword(''); setAgain('')
      await qc.invalidateQueries({ queryKey: ['current-user'] })
      onSuccess?.()
    },
  })
  const lengthError = password.length > 0 && (password.length < 8 || password.length > 128)
  const sameError = password.length > 0 && password === current
  const mismatch = again.length > 0 && password !== again
  const ready = current.length > 0 && password.length >= 8 && password.length <= 128 && password === again && password !== current
  return <form onSubmit={event => { event.preventDefault(); if (ready && !change.isPending) change.mutate() }}>
    <Stack gap="sm" dir="rtl">
      {temporary && <Text size="sm">رمز تحویل‌گرفته از مدیر موقت است. برای ادامه، رمز شخصی خود را تعیین کنید.</Text>}
      <PasswordInput label={temporary ? 'رمز موقت فعلی' : 'رمز عبور فعلی'} autoComplete="current-password"
        required maxLength={128} value={current} disabled={change.isPending} onChange={event => setCurrent(event.currentTarget.value)} />
      <PasswordInput label="رمز عبور جدید" description="۸ تا ۱۲۸ نویسه" autoComplete="new-password"
        required maxLength={128} value={password} disabled={change.isPending}
        error={lengthError ? 'رمز باید ۸ تا ۱۲۸ نویسه باشد' : sameError ? 'رمز جدید باید با رمز فعلی متفاوت باشد' : undefined}
        onChange={event => setPassword(event.currentTarget.value)} />
      <PasswordInput label="تکرار رمز عبور جدید" autoComplete="new-password"
        required maxLength={128} value={again} disabled={change.isPending} error={mismatch ? 'دو رمز عبور یکسان نیستند' : undefined}
        onChange={event => setAgain(event.currentTarget.value)} />
      {change.error && <Alert color="red">{errorMessage(change.error, 'تغییر رمز انجام نشد. دوباره تلاش کنید.')}</Alert>}
      {change.isSuccess && <Alert color="teal">رمز عبور تغییر کرد.</Alert>}
      <Group justify="flex-end">
        {onCancel && <Button variant="default" disabled={change.isPending} onClick={onCancel}>انصراف</Button>}
        <Button type="submit" loading={change.isPending} disabled={!ready}>ذخیره رمز جدید</Button>
      </Group>
    </Stack>
  </form>
}
