import type { CSSProperties } from 'react'
import { Check } from 'lucide-react'
import { modules } from '../modules'
import './TallyWorkflowStepper.css'

const stages = [
  { key: 'tally', label: 'تالی' },
  { key: 'ghabz', label: 'صدور قبض انبار' },
  { key: 'invoice', label: 'صدور صورتحساب' },
] as const

export function TallyWorkflowStepper({ tallyCreated, receiptsIssued, invoiceIssued }: {
  tallyCreated: boolean; receiptsIssued: boolean | null; invoiceIssued: boolean | null
}) {
  const completed = [tallyCreated, receiptsIssued, invoiceIssued]
  const current = completed.findIndex(done => done === false)
  return <ol className="tally-workflow-stepper" dir="rtl" aria-label="مراحل صدور اسناد تالی"
    aria-busy={completed.some(done => done === null)}>
    {stages.map((stage, index) => {
      const module = modules.find(item => item.key === stage.key)!
      const Icon = module.icon
      const done = completed[index]
      const status = done === null ? 'در حال بررسی' : done ? 'انجام‌شده' : 'انجام‌نشده'
      return <li key={stage.key} className="tally-workflow-step" data-completed={done === true}
        aria-current={index === current ? 'step' : undefined}
        aria-label={`${stage.label}: ${status}`} title={`${stage.label}: ${status}`}
        style={{ '--step-color': `var(--mantine-color-${module.color}-6)`,
          '--step-dark': `var(--mantine-color-${module.color}-8)` } as CSSProperties}>
        <span className="tally-workflow-step-icon" aria-hidden><Icon size={21} /></span>
        <span className="tally-workflow-step-label">{stage.label}</span>
        <span className="tally-workflow-step-status" aria-hidden>
          {done ? <Check size={15} strokeWidth={2.5} /> : done === null ? '…' : (index + 1).toLocaleString('fa-IR')}
        </span>
      </li>
    })}
  </ol>
}
