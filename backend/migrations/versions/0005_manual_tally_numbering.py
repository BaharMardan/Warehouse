"""Enable temporary manual tally entry without altering the automatic counter."""

def upgrade(cursor):
    cursor.execute('''INSERT INTO "FA_APP_SETTINGS"
        ("SETTING_KEY", "TITLE", "VALUE_NUMBER", "UNIT", "DESCRIPTION", "MODIFY_AT")
        VALUES ('manual_tally_numbering', :title, 1, NULL, :description, SYSDATE)''',
        {'title': 'شماره‌گذاری دستی تالی', 'description': 'ورود موقت شماره تالی به‌صورت دستی'})
