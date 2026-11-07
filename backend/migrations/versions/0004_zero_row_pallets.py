"""Allow explicit zero counts on shared-pallet rows without changing stock."""

def upgrade(cursor):
    for table, column, name in (
        ('FA_TALI_DETAILES', 'ROW_PALLETS', 'CK_TALLY_ROW_PALLETS_ZERO'),
        ('FA_RECEIPT_PALLETS', 'PALLETS', 'CK_RECEIPT_PALLETS_ZERO'),
    ):
        # Only replace the original single-column positive-integer check.
        cursor.execute("""SELECT c.CONSTRAINT_NAME, c.SEARCH_CONDITION_VC
            FROM USER_CONSTRAINTS c
            WHERE c.TABLE_NAME = :tab AND c.CONSTRAINT_TYPE = 'C'
              AND EXISTS (SELECT 1 FROM USER_CONS_COLUMNS cc
                WHERE cc.CONSTRAINT_NAME=c.CONSTRAINT_NAME AND cc.COLUMN_NAME=:col)""",
            {'tab': table, 'col': column})
        for constraint, condition in cursor.fetchall():
            normalized = ''.join(str(condition).upper().split()).replace('"', '')
            if normalized == f'{column}>=1AND{column}=TRUNC({column})':
                safe = constraint.replace('"', '""')
                cursor.execute(f'ALTER TABLE "{table}" DROP CONSTRAINT "{safe}"')
        cursor.execute(f'ALTER TABLE "{table}" ADD CONSTRAINT "{name}" '
                       f'CHECK ("{column}" >= 0 AND "{column}" = TRUNC("{column}"))')
