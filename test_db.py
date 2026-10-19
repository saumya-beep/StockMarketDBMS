from db import get_connection

try:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT USER FROM DUAL")
            print("Oracle connection successful!")
            print("Connected user:", cursor.fetchone()[0])

except Exception as error:
    print("Connection failed:")
    print(error)