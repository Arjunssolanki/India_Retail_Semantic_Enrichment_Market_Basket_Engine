import os
import boto3
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
from config.database_connection import get_database_engine

load_dotenv()

aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_region = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name=aws_region
)

bucket_name = "production-catalog-landing-zone"
file_key = "india_retail_sales_dataset.csv"

db_engine = get_database_engine("bronze")

def run_bronze_ingestion_pipeline():
    print("[INFO] Starting programmatic S3 streaming ingestion engine...")
    
    try:
        print(f"\n[INGESTION] Pulling active target object from AWS S3: {file_key}...")
        s3_object = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        df = pd.read_csv(s3_object["Body"])
        
        initial_row_count = len(df)
        df = df.drop_duplicates()
        df = df.fillna("NULL_FIELD_RECOVERED")
        
        # Swaps out all spaces for clean database underscores dynamically
        df.columns = [c.replace(' ', '_') for c in df.columns]
        
        table_target_name = "tbl_cleaned_retail_transactions"
        
        df.to_sql(
            name=table_target_name,
            con=db_engine,
            if_exists="replace",
            index=False,
            chunksize=1000
        )
        
        print(f"[SUCCESS] Ingested '{file_key}' safely into MySQL with clean underscores.")
        print(f" -> Columns Active: {list(df.columns)}")
        print(f" -> Rows Synchronized: {len(df)}")

    except Exception as ingestion_error:
        print(f"[WARN] S3 pipeline bypassed entity '{file_key}' due to error: {str(ingestion_error)}")

    print("\n[BRONZE INGESTION COMPLETE] Raw cloud baseline data sync loop finished.")

if __name__ == "__main__":
    run_bronze_ingestion_pipeline()
