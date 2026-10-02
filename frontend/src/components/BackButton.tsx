import { Button } from '@mantine/core'
import { useNavigate } from 'react-router-dom'
import { IconBack } from './icons'

/**
 * Consistent «بازگشت» button for detail/form sub-pages. Returns to the previous in-app history entry.
 * `to` is the fallback when the page was opened directly.
 */
export function BackButton({ to }: { to?: string }) {
  const navigate = useNavigate()
  return (
    <Button
      variant="default" radius="md" size="sm"
      leftSection={<IconBack size={16} />}
      onClick={() => {
        // React Router tracks the index of entries created within this app.
        // A directly opened page has no previous app entry to return to.
        if (typeof window.history.state?.idx === 'number' && window.history.state.idx > 0) {
          navigate(-1)
        } else {
          navigate(to ?? '/', { replace: true })
        }
      }}
    >
      بازگشت
    </Button>
  )
}