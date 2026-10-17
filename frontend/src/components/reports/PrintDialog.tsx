import { useState } from 'react'
import { Button, Checkbox, Group, Modal, Stack, Text } from '@mantine/core'
import { IconPrint } from '../icons'

export type PrintOption = { value: string; label: string; description?: string; disabled?: boolean }

/**
 * «چاپ» button that first asks which parts of the report go on the paper.
 * The report decides what each part means and builds the print link.
 */
export function PrintButton({ title, options, defaults, onPrint }: {
  title: string; options: PrintOption[]; defaults: string[]; onPrint: (sections: string[]) => void
}) {
  const [opened, setOpened] = useState(false)
  const [chosen, setChosen] = useState<string[]>(defaults)

  const open = () => { setChosen(defaults.filter((v) => options.some((o) => o.value === v && !o.disabled))); setOpened(true) }
  const ordered = options.map((o) => o.value).filter((v) => chosen.includes(v))

  return (
    <>
      <Button variant="light" color="forest" size="xs" leftSection={<IconPrint size={16} />} onClick={open}>چاپ</Button>
      <Modal opened={opened} onClose={() => setOpened(false)} title={title} dir="rtl" centered>
        <Stack gap="md">
          <Text size="sm" c="dimmed">بخش‌هایی را که می‌خواهید چاپ شود انتخاب کنید. بازه و فیلترهای فعلی همین صفحه اعمال می‌شوند.</Text>
          <Checkbox.Group value={chosen} onChange={setChosen}>
            <Stack gap="sm">
              {options.map((o) => (
                <Checkbox key={o.value} value={o.value} label={o.label} description={o.description} disabled={o.disabled} />
              ))}
            </Stack>
          </Checkbox.Group>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setOpened(false)}>انصراف</Button>
            <Button color="forest" leftSection={<IconPrint size={16} />} disabled={!ordered.length}
              onClick={() => { setOpened(false); onPrint(ordered) }}>مشاهدهٔ برگهٔ چاپ</Button>
          </Group>
        </Stack>
      </Modal>
    </>
  )
}
