import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_user = os.getenv("MYSQL_USER", "root")
db_password = os.getenv("MYSQL_ROOT_PASSWORD")
db_host = os.getenv("MYSQL_HOST", "127.0.0.1")
db_port = os.getenv("MYSQL_PORT", "3307")

base_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}"
engine = create_engine(base_url)

databases = ["india_retail_bronze", "india_retail_silver", "india_retail_gold"]

try:
    with engine.connect() as connection:
        for db in databases:
            connection.execute(text(f"CREATE DATABASE IF NOT EXISTS {db};"))
            connection.commit()
    print("[SUCCESS] All Medallion database layers successfully provisioned inside MySQL.")
except Exception as e:
    print(f"[ERROR] Database provisioning failed: {str(e)}")
