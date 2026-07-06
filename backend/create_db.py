import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Password")
DB_NAME = os.getenv("DB_NAME", "termscope")

try:
    print(f"Connecting to MySQL at {DB_HOST}:{DB_PORT} as {DB_USER}...")
    connection = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD
    )
    
    with connection.cursor() as cursor:
        print(f"Creating database '{DB_NAME}' if it does not exist...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        
    connection.commit()
    print("Database created successfully!")
    
except Exception as e:
    print(f"Error creating database: {e}")
finally:
    if 'connection' in locals() and connection.open:
        connection.close()
