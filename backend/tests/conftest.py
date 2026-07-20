from dotenv import load_dotenv

# Loads ORACLE_USER / ORACLE_PASSWORD / ORACLE_DSN from your .env file
# so the tests can connect to Oracle the same way your app does.
load_dotenv()
