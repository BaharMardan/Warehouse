/**
 * Permission codes the backend enforces (backend/app/auth/permissions.py).
 *
 * Same codes, same order. backend/tests/test_permissions.py fails if the two
 * lists drift apart, so a typo in can('...') is a compile error here and a
 * missing code is a failing test there. Persian labels live in the backend only.
 */
export const PERMISSION_CODES = [
  'kartabl.view',
  'base_data.edit',
  'commodity.manage',
  'tally.view',
  'tally.edit',
  'tally.delete',
  'tally.services',
  'ghabz.view',
  'ghabz.issue',
  'ghabz.edit',
  'invoice.view',
  'invoice.issue',
  'abandoned.view',
  'settings.manage',
] as const

export type PermissionCode = (typeof PERMISSION_CODES)[number]
