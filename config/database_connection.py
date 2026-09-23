import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

db_user = os.getenv("MYSQL_USER", "root")
db_password = os.getenv("MYSQL_ROOT_PASSWORD")
db_host = os.getenv("MYSQL_HOST", "127.0.0.1")
db_port = os.getenv("MYSQL_PORT", "3307")

DATABASE_URLS = {
    "bronze": f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/india_retail_bronze",
    "silver": f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/india_retail_silver",
    "gold": f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/india_retail_gold"
}

Base = declarative_base()

def get_database_engine(layer_name):
    if layer_name not in DATABASE_URLS:
        raise ValueError(f"Invalid layer boundary target: {layer_name}")
    
    engine = create_engine(
        DATABASE_URLS[layer_name],
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        pool_pre_ping=True
    )
    return engine

def get_database_session(layer_name):
    engine = get_database_engine(layer_name)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()
