import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "?sslmode=" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.split("?sslmode=")[0]

if not DATABASE_URL:
    print("Error: DATABASE_URL not found.")
    exit()

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with AsyncSessionLocal() as session:
        print("--- Updating Tables to Match Screenshots ---")
        
        # DROP tables first to ensure we recreate them with new columns
        # WARNING: This deletes existing data!
        await session.execute(text("DROP TABLE IF EXISTS raw_product_reviews CASCADE;"))
        await session.execute(text("DROP TABLE IF EXISTS \"Formatted_Review_dataset\" CASCADE;"))
        await session.execute(text("DROP TABLE IF EXISTS processed_product_reviews3 CASCADE;"))
        await session.execute(text("DROP TABLE IF EXISTS complaints CASCADE;"))
        await session.execute(text("DROP TABLE IF EXISTS amazon_reviews CASCADE;"))

        # 1. Raw Reviews
        await session.execute(text("""
            CREATE TABLE raw_product_reviews (
                "Review_id" INTEGER PRIMARY KEY,
                "Clothing ID" INTEGER,
                "Age" INTEGER,
                "Review_Text" TEXT,
                "Division Name" VARCHAR(255),
                "Department_Name" VARCHAR(255),
                "Class Name" VARCHAR(255),
                "Title" VARCHAR(255),
                "Rating" INTEGER
            );
        """))

        # 2. Formatted Reviews (Updated: Explicitly Nullable Columns)
        await session.execute(text("""
            CREATE TABLE "Formatted_Review_dataset" (
                "Review_id" INTEGER, 
                "Attribute" VARCHAR(255) NULL,
                "Score" INTEGER NULL,   -- Explicitly allows NULLs
                "Reason" TEXT NULL      -- Explicitly allows NULLs
            );
        """))

        # 3. Processed Reviews (Updated: Explicitly Nullable Columns)
        await session.execute(text("""
            CREATE TABLE processed_product_reviews3 (
                "reviewerID" VARCHAR(255),
                "ReviewTime" TIMESTAMP,
                "Category" VARCHAR(255) NULL, -- Explicitly allows NULLs
                "Attribute" VARCHAR(255) NULL,
                "Score" INTEGER NULL,         -- Explicitly allows NULLs
                "Reason" TEXT NULL,           -- Explicitly allows NULLs
                "Sortable Date" INTEGER
            );
        """))

        # 4. Complaints
        await session.execute(text("""
            CREATE TABLE complaints (
                complaint_text TEXT,
                predicted_category VARCHAR(255),
                predicted_intensity_label VARCHAR(50),
                predicted_intensity_score INTEGER,
                prediction_timestamp TIMESTAMP,
                customer_id VARCHAR(255),
                order_id VARCHAR(255),
                email_id VARCHAR(255)
            );
        """))

        # 5. Amazon Reviews
        await session.execute(text("""
            CREATE TABLE amazon_reviews (
                "reviewerID" VARCHAR(255),
                "asin" VARCHAR(255),
                "reviewerName" VARCHAR(255),
                "helpful" VARCHAR(255),
                "reviewText" TEXT,
                "overall" INTEGER,
                "summary" TEXT,
                "unixReviewTime" BIGINT,
                "reviewTime" TIMESTAMP
            );
        """))
        
        await session.commit()
        print("--- Tables Re-Created Successfully with Nullable Columns ---")

if __name__ == "__main__":
    asyncio.run(init_db())