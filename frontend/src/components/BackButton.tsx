import { Button } from '@mantine/core'
import { useNavigate } from 'react-router-dom'
import { IconBack } from './icons'

/**
 * Consistent «بازگشت» button for detail/form sub-pages. Pass `to` for an explicit
 * destination; otherwise it steps back in history.
 */
export function BackButton({ to }: { to?: string }) {
  const navigate = useNavigate()
  return (
    <Button
      variant="default" radius="md" size="sm"
      leftSection={<IconBack size={16} />}
      onClick={() => (to ? navigate(to) : navigate(-1))}
    >
      بازگشت
    </Button>
  )
}