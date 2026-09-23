import os
import pandas as pd
import mlflow
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from dotenv import load_dotenv
from config.database_connection import get_database_engine

load_dotenv()

db_engine_silver = get_database_engine("silver")
db_engine_gold = get_database_engine("gold")

def run_gold_analytics_pipeline():
    print("[INFO] Initializing Gold Layer Association Analytics Engine...")
    
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
    mlflow.set_experiment("/Production_Pipelines/Gold_Market_Basket_Analytics")
    
    min_support_value = 0.01
    min_confidence_value = 0.05
    
    with mlflow.start_run(run_name="market_basket_apriori_execution") as run:
        try:
            print("[INFO] Fetching feature tokens from Silver database schema...")
            silver_df = pd.read_sql("SELECT * FROM tbl_semantic_catalog_tokens", con=db_engine_silver)
            
            cat_col = "Category" if "Category" in silver_df.columns else "Sub_Category"
            loc_col = "City" if "City" in silver_df.columns else "State"
            
            silver_df["Composite_Basket_ID"] = silver_df[cat_col].astype(str) + "_" + silver_df[loc_col].astype(str)
            print(f"[INFO] Generated matching matrix composite vector: Composite_Basket_ID")
            
            transactions = silver_df.groupby("Composite_Basket_ID")["Extracted_Product_Type"].apply(list).tolist()
            total_baskets = len(transactions)
            
            mlflow.log_param("analytics_algorithm", "Apriori_Association_Rules")
            mlflow.log_param("minimum_support_threshold", min_support_value)
            mlflow.log_param("minimum_confidence_threshold", min_confidence_value)
            mlflow.log_param("total_transaction_baskets", total_baskets)
            
            print(f"[PROCESSING] Reshaping {total_baskets} transaction blocks into boolean matrix...")
            encoder = TransactionEncoder()
            matrix_array = encoder.fit(transactions).transform(transactions)
            matrix_df = pd.DataFrame(matrix_array, columns=encoder.columns_)
            
            print("[PROCESSING] Mining frequent itemsets via memory-restricted Apriori arrays...")
            frequent_itemsets = apriori(matrix_df, min_support=min_support_value, max_len=2, use_colnames=True)
            
            if len(frequent_itemsets) == 0:
                print("[WARN] Zero itemsets passed support limits. Deploying fallback database structure...")
                fallback_df = pd.DataFrame(columns=["antecedents", "consequents", "support", "confidence", "lift"])
                fallback_df.to_sql(name="tbl_market_basket_rules", con=db_engine_gold, if_exists="replace", index=False)
                mlflow.log_metric("total_association_rules_mined", 0)
                print("[SUCCESS] Empty fallback schema initialized successfully.")
                return

            print("[PROCESSING] Formulating business rules matrix structures...")
            rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_confidence_value)
            
            rules["antecedents"] = rules["antecedents"].apply(lambda x: ", ".join(list(x)))
            rules["consequents"] = rules["consequents"].apply(lambda x: ", ".join(list(x)))
            
            print("[INFO] Committing analytical insights rules table to Gold database schema...")
            rules.to_sql(
                name="tbl_market_basket_rules",
                con=db_engine_gold,
                if_exists="replace",
                index=False
            )
            
            total_rules = len(rules)
            max_lift = float(rules["lift"].max()) if total_rules > 0 else 0.0
            
            mlflow.log_metric("total_association_rules_mined", total_rules)
            mlflow.log_metric("maximum_lift_score", round(max_lift, 4))
            
            print("[SUCCESS] Gold analytical pipeline stage successfully verified.")
            print(f" -> Association Rules Extracted: {total_rules}")
            print(f" -> Max Lift Parameter Captured: {round(max_lift, 4)}")
            print(f" -> MLflow Core Registration Run ID: {run.info.run_id}")

        except Exception as stage_err:
            print(f"[ERROR] Gold analytical matrix operations crashed: {str(stage_err)}")
            mlflow.set_tag("pipeline_status", "FAILED")
            raise stage_err

if __name__ == "__main__":
    run_gold_analytics_pipeline()
