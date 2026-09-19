import { apiGet, apiSend } from './client'

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
  is_volumetric: 'yes' | 'no' | null
  volumetric_pallets: number | null
  goods_rows: number
}

export interface VolumetricAnswer {
  is_volumetric: 'yes' | 'no'
  volumetric_pallets: number | null
}

export const handoffKey = (tallyId: number | null | undefined) => ['tally-handoff', tallyId]
export const KEEPER_QUEUE_KEY = ['keeper-queue']

export const handoffApi = {
  read: (tallyId: number) => apiGet<HandoffState>(`/tally/${tallyId}/handoff`),
  sendToKeeper: (tallyId: number) =>
    apiSend<HandoffState>(`/tally/${tallyId}/handoff/send-to-keeper`, 'POST'),
  saveVolumetric: (tallyId: number, body: VolumetricAnswer) =>
    apiSend<HandoffState>(`/tally/${tallyId}/handoff/volumetric`, 'PUT', body),
  returnToOperator: (tallyId: number) =>
    apiSend<HandoffState>(`/tally/${tallyId}/handoff/return-to-operator`, 'POST'),
  keeperQueue: () => apiGet<{ waiting: number }>('/kartabl/keeper-queue'),
}
