type TallyNumberProps = {
  value: string | null | undefined
  fallback?: string
}

/**
 * Keeps the continuous number in logical left-to-right order when it is
 * embedded in the application's right-to-left Persian UI.
 */
export function TallyNumber({ value, fallback = '—' }: TallyNumberProps) {
  return (
    <bdi dir="ltr" style={{ display: 'inline-block', unicodeBidi: 'isolate' }}>
      {value || fallback}
    </bdi>
  )
}
