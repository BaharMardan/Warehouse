import { useQuery } from '@tanstack/react-query'
import { Avatar, Group, Select, Stack, Text } from '@mantine/core'
import { apiGet } from '../api/client'

export type InsuranceCompany = {
  id_insurance_company: number
  name: string
  logo_url: string | null
}

function InsuranceLogo({ company, size = 34 }: { company: InsuranceCompany; size?: number }) {
  return (
    <Avatar src={company.logo_url || undefined} alt={`آرم ${company.name}`} size={size} radius="md" color="blue">
      {company.name.trim().slice(0, 1)}
    </Avatar>
  )
}

/** Selects an insurer by name because existing tally headers store COMPANY_BIMEH as text. */
export function InsuranceCompanySelect({
  value,
  onChange,
}: {
  value: string
  onChange: (value: string) => void
}) {
  const { data = [], isLoading } = useQuery({
    queryKey: ['insurance-companies'],
    queryFn: () => apiGet<InsuranceCompany[]>('/insurance-companies'),
    staleTime: 5 * 60 * 1000,
  })

  const selectedFromCatalog = data.find((company) => company.name === value)
  // Keep legacy tally values visible even if that insurer has not yet been added
  // to the new base-data catalog.
  const companies = selectedFromCatalog || !value.trim()
    ? data
    : [{ id_insurance_company: -1, name: value, logo_url: null }, ...data]
  const selected = companies.find((company) => company.name === value)
  const options = companies.map((company) => ({
    value: String(company.id_insurance_company),
    label: company.name,
  }))

  return (
    <Select
      label="شرکت بیمه‌گر"
      placeholder="شرکت بیمه‌گر را انتخاب کنید"
      data={options}
      value={selected ? String(selected.id_insurance_company) : null}
      onChange={(id) => onChange(companies.find((company) => String(company.id_insurance_company) === id)?.name ?? '')}
      renderOption={({ option }) => {
        const company = companies.find((item) => String(item.id_insurance_company) === option.value)
        if (!company) return option.label
        return (
          <Group gap="sm" wrap="nowrap">
            <InsuranceLogo company={company} />
            <Stack gap={0}>
              <Text size="sm" fw={600}>{company.name}</Text>
              <Text size="xs" c="dimmed">شرکت بیمه</Text>
            </Stack>
          </Group>
        )
      }}
      leftSection={selected ? <InsuranceLogo company={selected} size={26} /> : undefined}
      searchable
      clearable
      disabled={isLoading}
      nothingFoundMessage="شرکت بیمه‌ای یافت نشد"
    />
  )
}
