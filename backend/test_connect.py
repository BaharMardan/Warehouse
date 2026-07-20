import oracledb

print(oracledb.__version__)

conn = oracledb.connect(
    user="hr",
    password="oracle",
    host="192.168.1.115",
    port=1521,
    service_name="freepdb1",
)

print("CONNECTED")
conn.close()

# import oracledb

# conn = oracledb.connect(
#     user="hr",
#     password="oracle",
#     dsn="192.168.1.115:1521/freepdb1"
# )

# print("connected")

