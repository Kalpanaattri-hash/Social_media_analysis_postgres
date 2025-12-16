import asyncio
import os
import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

# --- 1. Database Connection ---
DATABASE_URL = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "?sslmode=" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.split("?sslmode=")[0]

if not DATABASE_URL:
    print("Error: DATABASE_URL not found. Make sure .env exists.")
    exit()

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# --- Helper Functions ---
def get_val(row, keys, default=None):
    """Tries multiple column name variations to find data."""
    for k in keys:
        if k in row:
            val = row[k]
            # Check for pandas NaN (Not a Number) or empty string
            if pd.notna(val) and str(val).strip() != "":
                return val
    return default

def safe_int(val):
    """Safely converts to int, returning None (NULL) if invalid."""
    if val is None:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None

def parse_date(date_str):
    """Converts a date string into a naive Python datetime object."""
    if not date_str or pd.isna(date_str):
        return datetime.now().replace(tzinfo=None)
    try:
        dt = pd.to_datetime(date_str).to_pydatetime()
        return dt.replace(tzinfo=None)
    except:
        return datetime.now().replace(tzinfo=None)

# --- 2. Import Functions ---

async def import_raw_reviews():
    filename = "raw_product_reviews.csv"
    if not os.path.exists(filename): return print(f"Skipping {filename} (Not found)...")
    print(f"--- Importing {filename} (Batch Mode) ---")
    
    df = pd.read_csv(filename)
    data_batch = []
    
    async with AsyncSessionLocal() as session:
        for index, row in df.iterrows():
            rid = safe_int(get_val(row, ["Review_id", "Review ID", "id"], 0))
            if not rid: continue 

            item = {
                "rid": rid,
                "cid": safe_int(get_val(row, ["Clothing ID", "Clothing Id"], 0)),
                "age": safe_int(get_val(row, ["Age", "age"], 0)),
                "txt": str(get_val(row, ["Review_Text", "Review Text", "text"], "")),
                "div": str(get_val(row, ["Division Name", "Division"], "")),
                "dept": str(get_val(row, ["Department_Name", "Department Name", "department"], "")),
                "cls": str(get_val(row, ["Class Name", "Class"], "")),
                "title": str(get_val(row, ["Title", "title"], "")),
                "rate": safe_int(get_val(row, ["Rating", "rating"], 0))
            }
            data_batch.append(item)

            if len(data_batch) >= 1000:
                await session.execute(text("""
                    INSERT INTO raw_product_reviews ("Review_id", "Clothing ID", "Age", "Review_Text", 
                        "Division Name", "Department_Name", "Class Name", "Title", "Rating")
                    VALUES (:rid, :cid, :age, :txt, :div, :dept, :cls, :title, :rate)
                    ON CONFLICT ("Review_id") DO NOTHING
                """), data_batch)
                await session.commit()
                print(f"... Inserted batch of {len(data_batch)} rows")
                data_batch = [] 

        if data_batch:
            await session.execute(text("""
                INSERT INTO raw_product_reviews ("Review_id", "Clothing ID", "Age", "Review_Text", 
                    "Division Name", "Department_Name", "Class Name", "Title", "Rating")
                VALUES (:rid, :cid, :age, :txt, :div, :dept, :cls, :title, :rate)
                ON CONFLICT ("Review_id") DO NOTHING
            """), data_batch)
            await session.commit()
    print("Done.")

async def import_formatted_reviews():
    filename = "Formatted_Review_dataset.csv"
    if not os.path.exists(filename): return print(f"Skipping {filename} (Not found)...")
    print(f"--- Importing {filename} (Batch Mode) ---")
    
    df = pd.read_csv(filename)
    data_batch = []
    
    async with AsyncSessionLocal() as session:
        for index, row in df.iterrows():
            rid = safe_int(get_val(row, ["Review_id", "Review ID"], 0))
            if not rid: continue

            item = {
                "rid": rid,
                "attr": str(get_val(row, ["Attribute", "attribute"], "")),
                "score": safe_int(get_val(row, ["Score", "score"], None)), 
                "reason": str(get_val(row, ["Reason", "reason"], ""))
            }
            data_batch.append(item)

            if len(data_batch) >= 1000:
                await session.execute(text("""
                    INSERT INTO "Formatted_Review_dataset" ("Review_id", "Attribute", "Score", "Reason")
                    VALUES (:rid, :attr, :score, :reason)
                """), data_batch)
                await session.commit()
                print(f"... Inserted batch of {len(data_batch)} rows")
                data_batch = []

        if data_batch:
            await session.execute(text("""
                INSERT INTO "Formatted_Review_dataset" ("Review_id", "Attribute", "Score", "Reason")
                VALUES (:rid, :attr, :score, :reason)
            """), data_batch)
            await session.commit()
    print("Done.")

async def import_processed_reviews():
    filename = "processed_product_reviews3.csv"
    if not os.path.exists(filename): return print(f"Skipping {filename} (Not found)...")
    print(f"--- Importing {filename} (Batch Mode) ---")
    
    df = pd.read_csv(filename)
    data_batch = []
    
    async with AsyncSessionLocal() as session:
        for index, row in df.iterrows():
            time_str = str(get_val(row, ["ReviewTime", "Review Time", "time"]))
            time_val = parse_date(time_str)

            item = {
                "rid": str(get_val(row, ["reviewerID", "Review_id"], "")),
                "time": time_val, 
                "cat": str(get_val(row, ["Category", "category"], "")),
                "attr": str(get_val(row, ["Attribute", "attribute"], "")),
                "score": safe_int(get_val(row, ["Score", "score"], None)),
                "reason": str(get_val(row, ["Reason", "reason"], "")),
                "sdate": safe_int(get_val(row, ["Sortable Date", "sortable_date"], 0))
            }
            data_batch.append(item)

            if len(data_batch) >= 1000:
                await session.execute(text("""
                    INSERT INTO processed_product_reviews3 (
                        "reviewerID", "ReviewTime", "Category", "Attribute", "Score", "Reason", "Sortable Date"
                    )
                    VALUES (:rid, :time, :cat, :attr, :score, :reason, :sdate)
                """), data_batch)
                await session.commit()
                print(f"... Inserted batch of {len(data_batch)} rows")
                data_batch = []

        if data_batch:
            await session.execute(text("""
                INSERT INTO processed_product_reviews3 (
                    "reviewerID", "ReviewTime", "Category", "Attribute", "Score", "Reason", "Sortable Date"
                )
                VALUES (:rid, :time, :cat, :attr, :score, :reason, :sdate)
            """), data_batch)
            await session.commit()
    print("Done.")

async def import_complaints():
    filename = "complaints.csv"
    if not os.path.exists(filename): return print(f"Skipping {filename} (Not found)...")
    print(f"--- Importing {filename} (Batch Mode) ---")
    
    df = pd.read_csv(filename)
    data_batch = []
    
    async with AsyncSessionLocal() as session:
        for index, row in df.iterrows():
            time_str = str(get_val(row, ["prediction_timestamp", "Timestamp"]))
            time_val = parse_date(time_str)

            item = {
                "txt": str(get_val(row, ["complaint_text", "Complaint Text"], "")),
                "cat": str(get_val(row, ["predicted_category", "Category"], "")),
                "label": str(get_val(row, ["predicted_intensity_label", "Intensity Label"], "")),
                "score": safe_int(get_val(row, ["predicted_intensity_score", "Score"], 0)),
                "time": time_val,
                "cid": str(get_val(row, ["customer_id", "Customer ID"], "")),
                "oid": str(get_val(row, ["order_id", "Order ID"], "")),
                "eid": str(get_val(row, ["email_id", "Email ID"], ""))
            }
            data_batch.append(item)

            if len(data_batch) >= 1000:
                await session.execute(text("""
                    INSERT INTO complaints (
                        complaint_text, predicted_category, predicted_intensity_label, 
                        predicted_intensity_score, prediction_timestamp, customer_id, order_id, email_id
                    )
                    VALUES (:txt, :cat, :label, :score, :time, :cid, :oid, :eid)
                """), data_batch)
                await session.commit()
                print(f"... Inserted batch of {len(data_batch)} rows")
                data_batch = []

        if data_batch:
            await session.execute(text("""
                INSERT INTO complaints (
                    complaint_text, predicted_category, predicted_intensity_label, 
                    predicted_intensity_score, prediction_timestamp, customer_id, order_id, email_id
                )
                VALUES (:txt, :cat, :label, :score, :time, :cid, :oid, :eid)
            """), data_batch)
            await session.commit()
    print("Done.")

async def import_amazon_reviews():
    filename = "amazon_reviews.csv"
    if not os.path.exists(filename): return print(f"Skipping {filename} (Not found)...")
    print(f"--- Importing {filename} (Batch Mode) ---")
    
    df = pd.read_csv(filename)
    data_batch = []
    
    async with AsyncSessionLocal() as session:
        for index, row in df.iterrows():
            time_str = str(get_val(row, ["reviewTime", "Review Time", "time"]))
            time_val = parse_date(time_str)

            item = {
                "rid": str(get_val(row, ["reviewerID", "Reviewer ID"], "")),
                "asin": str(get_val(row, ["asin", "ASIN"], "")),
                "name": str(get_val(row, ["reviewerName", "Reviewer Name"], "")),
                "help": str(get_val(row, ["helpful", "Helpful"], "")),
                "txt": str(get_val(row, ["reviewText", "Review Text"], "")),
                "ovr": safe_int(get_val(row, ["overall", "Overall", "Rating"], 0)),
                "summ": str(get_val(row, ["summary", "Summary"], "")),
                "unix": safe_int(get_val(row, ["unixReviewTime", "Unix Time"], 0)),
                "time": time_val
            }
            data_batch.append(item)

            if len(data_batch) >= 1000:
                # FIXED: Quotes used for column names to match Postgres case-sensitivity
                # FIXED: Parameters (:rid, :asin...) now match the dictionary keys
                await session.execute(text("""
                    INSERT INTO amazon_reviews (
                        "reviewerID", asin, "reviewerName", helpful, "reviewText", 
                        overall, summary, "unixReviewTime", "reviewTime"
                    )
                    VALUES (:rid, :asin, :name, :help, :txt, :ovr, :summ, :unix, :time)
                """), data_batch)
                await session.commit()
                print(f"... Inserted batch of {len(data_batch)} rows")
                data_batch = []

        if data_batch:
            # FIXED: Quotes used for column names
            await session.execute(text("""
              INSERT INTO amazon_reviews (
                "reviewerID", asin, "reviewerName", helpful, "reviewText",
                 overall, summary, "unixReviewTime", "reviewTime"
              )
            VALUES (:rid, :asin, :name, :help, :txt, :ovr, :summ, :unix, :time)
            """), data_batch)
            await session.commit()
    print("Done.")

# --- 3. Main Execution ---
async def main():
    print("--- Resuming Upload... ---")
    
    # --- SKIPPING COMPLETED TABLES ---
    # The following functions are commented out because you have already 
    # successfully uploaded these files.
    
    # await import_raw_reviews()
    
    # async with AsyncSessionLocal() as session:
    #     print("Cleaning up partial data in 'Formatted_Review_dataset'...")
    #     await session.execute(text('TRUNCATE TABLE "Formatted_Review_dataset"'))
    #     await session.commit()
    
    # await import_formatted_reviews()
    # await import_processed_reviews()
    # await import_complaints()
    
    # --- ONLY RUNNING AMAZON REVIEWS ---
    await import_amazon_reviews()
    
    print("--- Amazon Reviews Seeded Successfully ---")

if __name__ == "__main__":
    try:
        # Windows-specific fix for "Event Loop" errors
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except:
        pass
    asyncio.run(main())