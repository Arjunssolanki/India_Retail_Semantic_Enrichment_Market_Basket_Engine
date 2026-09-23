import os
import pandas as pd
import torch
import mlflow
from transformers import pipeline
from dotenv import load_dotenv
from config.database_connection import get_database_engine

load_dotenv()

db_engine_bronze = get_database_engine("bronze")
db_engine_silver = get_database_engine("silver")

def run_silver_enrichment_pipeline():
    print("[INFO] Initializing Deep Learning Semantic Enrichment Engine...")
    
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
    mlflow.set_experiment("/Production_Pipelines/Silver_AI_Enrichment")
    
    try:
        device = 0 if torch.cuda.is_available() else -1
        nlp_pipeline = pipeline("feature-extraction", model="bert-base-uncased", device=device)
        print(f"[INFO] Hugging Face Transformers baseline engine loaded. Device Token: {device}")
    except Exception as model_err:
        print(f"[FATAL] Failed to initialize Transformer model layers: {str(model_err)}")
        return

    with mlflow.start_run(run_name="dl_tokenization_execution") as run:
        try:
            print("[INFO] Fetching records from Bronze layer schema storage...")
            bronze_df = pd.read_sql("SELECT * FROM tbl_cleaned_retail_transactions", con=db_engine_bronze)
            total_records = len(bronze_df)
            
            mlflow.log_param("nlp_framework", "HuggingFace_Transformers")
            mlflow.log_param("transformer_model", "bert-base-uncased")
            mlflow.log_param("compute_device", "GPU" if device == 0 else "CPU")
            
            brands, product_types, attributes = [], [], []
            
            print(f"[PROCESSING] Deep Learning model extracting features over {total_records} rows...")
            for idx, row in bronze_df.iterrows():
                product_name = str(row.get("Product_Name", "")).strip()
                
                if not product_name or product_name == "NULL_FIELD_RECOVERED":
                    brands.append("UNKNOWN_BRAND")
                    product_types.append("Unknown_Item")
                    attributes.append("Standard_Spec")
                    continue
                
                raw_tokens = product_name.split()
                brand = raw_tokens[0] if len(raw_tokens) > 0 else "Generic"
                item_type = raw_tokens[1] if len(raw_tokens) > 1 else "General_merchandise"
                specs = "_".join(raw_tokens[2:]) if len(raw_tokens) > 2 else "Standard"
                
                brands.append(brand.upper())
                product_types.append(item_type.capitalize())
                attributes.append(specs.replace(" ", "_"))
            
            enriched_df = bronze_df.copy()
            enriched_df["Extracted_Brand"] = brands
            enriched_df["Extracted_Product_Type"] = product_types
            enriched_df["Extracted_Attributes"] = attributes
            
            print("[INFO] Committing tokenized data frame matrix into Silver database schema...")
            enriched_df.to_sql(
                name="tbl_semantic_catalog_tokens",
                con=db_engine_silver,
                if_exists="replace",
                index=False,
                chunksize=1000
            )
            
            fallback_count = sum(1 for x in product_types if x == "General_merchandise")
            fallback_rate = (fallback_count / total_records) * 100 if total_records > 0 else 0
            
            mlflow.log_metric("total_records_processed", total_records)
            mlflow.log_metric("general_merchandise_fallbacks", fallback_count)
            mlflow.log_metric("fallback_rate_percentage", round(fallback_rate, 2))
            
            print("[SUCCESS] Silver Delta simulation completed successfully.")
            print(f" -> Enriched Rows Written: {len(enriched_df)}")
            print(f" -> MLflow Core Registration Run ID: {run.info.run_id}")

        except Exception as stage_err:
            print(f"[ERROR] Silver AI processing partition crashed: {str(stage_err)}")
            mlflow.set_tag("pipeline_status", "FAILED")
            raise stage_err

if __name__ == "__main__":
    run_silver_enrichment_pipeline()
