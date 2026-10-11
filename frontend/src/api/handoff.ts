import { apiGet, apiSend } from './client'
import type { PalletRow, PalletEntry } from '../components/PalletRows'

/** The operator / warehouse-keeper handoff on one tally (see app/routers/tally_handoff.py). */

export type HandoffStep = 'operator' | 'keeper' | 'returned'

export interface HandoffState {
  id_tali: number
  step: HandoffStep
  sent_to_keeper_at: string | null
  /** Persian calendar date/time formatted by the database server. */
  sent_to_keeper_at_display: string | null
  sent_to_keeper_by: string | null
  returned_at: string | null
  /** Persian calendar date/time formatted by the database server. */
  returned_at_display: string | null
  returned_by: string | null
  cargo_type: 'weight' | 'volumetric' | 'container' | null
  volumetric_pallets: number | null
  pallet_rows: PalletRow[]
  can_edit_pallets: boolean
  goods_rows: number
  has_receipts: boolean
  can_edit_goods: boolean
  active_invoice_count: number
  can_edit_services: boolean
  receipt_checklists: { id: number; number: string | null; status: string }[]
}

export interface CargoTypeAnswer {
  cargo_type: 'weight' | 'volumetric' | 'container'
  volumetric_pallets: number | null
}

export const handoffKey = (tallyId: number | null | undefined) => ['tally-handoff', tallyId]
export const KEEPER_QUEUE_KEY = ['keeper-queue']

export const handoffApi = {
  read: (tallyId: number) => apiGet<HandoffState>(`/tally/${tallyId}/handoff`),
  sendToKeeper: (tallyId: number) =>
    apiSend<HandoffState>(`/tally/${tallyId}/handoff/send-to-keeper`, 'POST'),
  saveCargoType: (tallyId: number, body: CargoTypeAnswer) =>
    apiSend<HandoffState>(`/tally/${tallyId}/handoff/volumetric`, 'PUT', body),
  savePalletRows: (tallyId: number, lines: PalletEntry[]) =>
    apiSend<HandoffState>(`/tally/${tallyId}/handoff/pallets`, 'PUT', { lines }),
  returnToOperator: (tallyId: number) =>
    apiSend<HandoffState>(`/tally/${tallyId}/handoff/return-to-operator`, 'POST'),
  keeperQueue: () => apiGet<{ waiting: number }>('/kartabl/keeper-queue'),
}
