import os
import sys
import time
import pandas as pd
from config.database_connection import get_database_engine

def execute_medallion_pipeline():
    print("=" * 80)
    print("[ORCHESTRATOR] INITIATING END-TO-END MEDALLION DATA PIPELINE TRACK RUN")
    print("=" * 80)
    
    pipeline_stages = [
        {"name": "Database Schema Bootstrapping", "script": "bootstrap_databases.py"},
        {"name": "Bronze Layer Ingestion (AWS S3 -> MySQL)", "script": "01_bronze_ingestion.py"},
        {"name": "Silver Layer AI Enrichment (Transformers -> MLflow)", "script": "02_silver_dl_enrichment.py"},
        {"name": "Gold Layer Analytics (Apriori -> MLflow)", "script": "03_gold_association_rules.py"}
    ]
    
    start_time = time.time()
    
    for stage in pipeline_stages:
        stage_name = stage["name"]
        script_file = stage["script"]
        
        print(f"\n[ORCHESTRATOR] Entering Stage Execution Window: {stage_name}...")
        
        if not os.path.exists(script_file):
            print(f"[FATAL ERROR] Pipeline script target execution file not found: {script_file}")
            sys.exit(1)
            
        execution_status = os.system(f"python {script_file}")
        
        if execution_status != 0:
            print(f"\n[FATAL ERROR] Pipeline execution halted! Stage '{stage_name}' failed with code: {execution_status}")
            sys.exit(1)
            
        print(f"[STAGE SUCCESS] Completed boundary phase: {stage_name}")
        
    print("\n" + "-" * 80)
    print("[ORCHESTRATOR] EXECUTING SECURE TRACKING ASSET GENERATION PORTS")
    print("-" * 80)
    
    assets_dir = "assets"
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)
        print(f"[INFO] Initialized new target tracking asset directory boundary: {assets_dir}")
        
    try:
        engine_bronze = get_database_engine("bronze")
        df_bronze = pd.read_sql("SELECT * FROM tbl_cleaned_retail_transactions", con=engine_bronze)
        df_bronze.to_csv(os.path.join(assets_dir, "data_ingestion.csv"), index=False)
        print("[SUCCESS] Exported structural snapshot: assets/data_ingestion.csv")
        
        engine_silver = get_database_engine("silver")
        df_silver = pd.read_sql("SELECT * FROM tbl_semantic_catalog_tokens", con=engine_silver)
        df_silver.to_csv(os.path.join(assets_dir, "silver_layer.csv"), index=False)
        print("[SUCCESS] Exported deep learning snapshot: assets/silver_layer.csv")
        
        engine_gold = get_database_engine("gold")
        df_gold = pd.read_sql("SELECT * FROM tbl_market_basket_rules", con=engine_gold)
        df_gold.to_csv(os.path.join(assets_dir, "gold_layer.csv"), index=False)
        print("[SUCCESS] Exported analytical market rules snapshot: assets/gold_layer.csv")
        
    except Exception as asset_error:
        print(f"[WARN] Portfolio asset tracking extraction bypassed due to runtime exception: {str(asset_error)}")
        
    end_time = time.time()
    total_elapsed = end_time - start_time
    
    print("\n" + "=" * 80)
    print(f"[SUCCESS] PIPELINE RUN COMPLETE | RUNTIME DETECTOR: {round(total_elapsed, 2)} SECONDS")
    print("=" * 80)

if __name__ == "__main__":
    execute_medallion_pipeline()
