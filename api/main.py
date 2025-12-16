from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import re
import json
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, List, Any
from dotenv import load_dotenv
import google.generativeai as genai
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

load_dotenv()

# --- 1. CONFIGURATION ---
DATABASE_URL = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "?sslmode=" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.split("?sslmode=")[0]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

AVAILABLE_TABLES = {
    "Processed Product Reviews": "processed_product_reviews3",
    "Formatted Review Dataset": "Formatted_Review_dataset",
    "Complaints Data": "complaints",
    "Amazon Reviews": "amazon_reviews",
    "Raw Reviews": "raw_product_reviews"
}

# Schemas for Chatbot Context
TABLE_SCHEMAS = {
    "processed_product_reviews3": """
        "reviewerID" (TEXT), "ReviewTime" (TIMESTAMP), "Category" (TEXT), 
        "Attribute" (TEXT), "Score" (INTEGER), "Reason" (TEXT), "Sortable Date" (INTEGER)
    """,
    '"Formatted_Review_dataset"': """
        "Review_id" (INTEGER), "Attribute" (TEXT), "Score" (INTEGER), "Reason" (TEXT)
    """,
    "complaints": """
        complaint_text (TEXT), predicted_category (TEXT), predicted_intensity_label (TEXT),
        predicted_intensity_score (INTEGER), prediction_timestamp (TIMESTAMP),
        customer_id (TEXT), order_id (TEXT), email_id (TEXT)
    """,
    "amazon_reviews": """
        reviewerID (TEXT), asin (TEXT), reviewText (TEXT), overall (INTEGER),
        summary (TEXT), reviewTime (TIMESTAMP)
    """,
    "raw_product_reviews": """
        "Review_id" (INTEGER), "Review_Text" (TEXT), "Division Name" (TEXT),
        "Department_Name" (TEXT), "Class Name" (TEXT), "Rating" (INTEGER), "Age" (INTEGER)
    """
}

app = FastAPI(title="Review Analytics API", version="7.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. DATABASE ENGINE ---
engine = None
AsyncSessionLocal = None
if DATABASE_URL:
    try:
        engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
        AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    except Exception as e:
        print(f"DB Init Error: {e}")

# --- 3. MODELS ---
class ChatRequest(BaseModel):
    prompt: str
class ChatResponse(BaseModel):
    results_html: Optional[str] = None
    insights: Optional[str] = None
    error: Optional[str] = None
class InsightRequest(BaseModel):
    page_key: str
class InsightResponse(BaseModel):
    insights: Optional[str] = None
    error: Optional[str] = None

# --- 4. HELPER FUNCTIONS ---
def get_gemini_analyzer():
    try:
        return genai.GenerativeModel(GEMINI_MODEL_NAME)
    except:
        return genai.GenerativeModel("gemini-1.5-flash")

async def run_sql_query(query_text: str) -> List[dict]:
    """Runs SQL and handles Decimal/Date serialization."""
    if not AsyncSessionLocal: return []
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(text(query_text))
            keys = result.keys()
            rows = result.fetchall()
            clean = []
            for row in rows:
                row_dict = {}
                for key, val in zip(keys, row):
                    if isinstance(val, Decimal): row_dict[key] = float(val)
                    elif isinstance(val, (date, datetime)): row_dict[key] = val.isoformat()
                    else: row_dict[key] = val
                clean.append(row_dict)
            return clean
        except Exception as e:
            print(f"SQL Error: {e}")
            return []

def clean_sql_query(raw_sql: str) -> str:
    cleaned = re.sub(r"```sql\n?", "", raw_sql, flags=re.IGNORECASE)
    cleaned = re.sub(r"```", "", cleaned)
    match = re.search(r"(SELECT\s.*)", cleaned, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else cleaned.strip()

def format_results_to_html(results: List[dict]) -> str:
    if not results: return ""
    headers = list(results[0].keys())
    # Normalize headers: remove underscores and capitalize words
    def _pretty(h):
        try:
            s = str(h).replace('_', ' ').strip()
            return s.title()
        except Exception:
            return str(h)

    pretty_headers = [_pretty(h) for h in headers]

    html = "<div style='overflow-x:auto'><table style='width:100%; border-collapse:collapse; color:white; font-size:0.9rem;'>"
    html += "<thead><tr style='background:#374151; text-align: left;'>" + "".join(f"<th style='padding:12px; border-bottom: 2px solid #4B5563;'>{ph}</th>" for ph in pretty_headers) + "</tr></thead>"
    html += "<tbody>"
    for i, row in enumerate(results):
        bg = "#1F2937" if i % 2 == 0 else "#2D3748"
        html += f"<tr style='background:{bg}; border-bottom:1px solid #4B5563'>" + "".join(f"<td style='padding:10px;'>{v}</td>" for v in row.values()) + "</tr>"
    html += "</tbody></table></div>"
    return html

def clean_gemini_response(text: str) -> str:
    text = text.replace("```markdown", "").replace("```", "").strip()
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith('**') or line.strip().startswith('1.') or "**" in line:
            return '\n'.join(lines[i:]).strip()
        if "okay" in line.lower() or "ready" in line.lower(): continue
    return text

def format_results_to_string(results: List[dict]) -> str:
    if not results: return ""
    headers = list(results[0].keys())
    # Normalize headers for LLM consumption (no underscores, capitalized)
    def _pretty(h):
        try:
            return str(h).replace('_', ' ').strip().title()
        except Exception:
            return str(h)

    pretty_headers = [_pretty(h) for h in headers]
    rows = [" | ".join(map(str, r.values())) for r in results]
    return " | ".join(pretty_headers) + "\n" + "\n".join(rows)

def get_table_schema(table_name: str) -> str:
    clean_name = table_name.replace("'", "").replace('"', '')
    for key, schema in TABLE_SCHEMAS.items():
        if clean_name.lower() in key.lower():
            return schema
    return "Schema not found."

# --- 5. DASHBOARD DATA FETCHERS (ALIGNED WITH YOUR LOGIC) ---

async def get_social_dashboard_data() -> dict:
    """Queries raw_product_reviews + Formatted_Review_dataset"""
    print("--- Fetching Social Data ---")
    
    pie = await run_sql_query('SELECT "Attribute", COUNT(*) as count FROM "Formatted_Review_dataset" WHERE "Attribute" IS NOT NULL GROUP BY 1 ORDER BY 2 DESC')
    bar = await run_sql_query('SELECT "Score", "Attribute", COUNT(*) as count FROM "Formatted_Review_dataset" WHERE "Attribute" IS NOT NULL AND "Score" IS NOT NULL GROUP BY 1, 2 ORDER BY 1 DESC, 3 DESC')
    age = await run_sql_query("""SELECT CASE WHEN "Age" BETWEEN 18 AND 25 THEN '18-25' WHEN "Age" BETWEEN 26 AND 35 THEN '26-35' WHEN "Age" BETWEEN 36 AND 50 THEN '36-50' ELSE '51+' END AS age_group, f."Attribute", AVG(f."Score") AS score FROM "Formatted_Review_dataset" f LEFT JOIN raw_product_reviews r ON f."Review_id" = r."Review_id" WHERE f."Attribute" IS NOT NULL AND f."Score" IS NOT NULL GROUP BY 1, 2""")
    scatter = await run_sql_query("""SELECT COALESCE(r."Department_Name", 'Unknown') AS department, COUNT(f."Review_id") AS num_reviews, AVG(f."Score") AS avg_score FROM "Formatted_Review_dataset" f LEFT JOIN raw_product_reviews r ON f."Review_id" = r."Review_id" WHERE f."Score" IS NOT NULL GROUP BY 1""")
    matrix = await run_sql_query("""SELECT COALESCE(r."Department_Name", 'Unknown') as "Department", f."Attribute", AVG(f."Score") as "Sentiment_Score", COUNT(f."Review_id") as "Volume" FROM "Formatted_Review_dataset" f LEFT JOIN raw_product_reviews r ON f."Review_id" = r."Review_id" WHERE f."Score" IS NOT NULL GROUP BY 1, 2 HAVING COUNT(f."Review_id") > 3 ORDER BY "Department", "Sentiment_Score" ASC""")
    text_d = await run_sql_query('SELECT f."Attribute", COALESCE(r."Review_Text", \'No text\') AS "Review_Text", f."Score" FROM "Formatted_Review_dataset" f LEFT JOIN raw_product_reviews r ON f."Review_id" = r."Review_id" WHERE f."Score" IS NOT NULL ORDER BY f."Score" DESC LIMIT 10')
    perf = await run_sql_query('SELECT COALESCE(r."Department_Name", \'Unknown\') AS "Department", COUNT(f."Review_id") AS num_reviews, ROUND(AVG(f."Score"), 2) AS "Average_Score" FROM "Formatted_Review_dataset" f LEFT JOIN raw_product_reviews r ON f."Review_id" = r."Review_id" WHERE f."Score" IS NOT NULL GROUP BY 1 ORDER BY 2 DESC')

    total = sum(x['count'] for x in pie) if pie else 0
    pie_final = [{**item, "percentage": round((item['count']/total)*100, 1)} for item in pie]
    
    return {"page1": {"total": total, "pie": pie_final, "bar": bar, "age": age, "scatter": scatter, "matrix": matrix}, "page2": {"total": total, "text": text_d, "perf": perf}}

async def get_trend_dashboard_data() -> dict:
    """Queries processed_product_reviews3 + amazon_reviews (optional blend)"""
    print("--- Fetching Trend Data ---")
    
    # Using processed_product_reviews3 for consistent time-series metrics
    line = await run_sql_query('SELECT TO_CHAR("ReviewTime", \'YYYY-MM\') AS date, "Attribute", AVG("Score") AS score FROM processed_product_reviews3 WHERE "ReviewTime" IS NOT NULL GROUP BY 1, 2 ORDER BY 1, 2')
    pivot = await run_sql_query("SELECT CAST(EXTRACT(YEAR FROM \"ReviewTime\") AS VARCHAR) || '/Q' || CAST(EXTRACT(QUARTER FROM \"ReviewTime\") AS VARCHAR) AS \"Quarter\", AVG(CASE WHEN LOWER(\"Attribute\") LIKE '%comfort%' THEN \"Score\" ELSE NULL END) AS \"Comfort\", AVG(CASE WHEN LOWER(\"Attribute\") LIKE '%design%' THEN \"Score\" ELSE NULL END) AS \"Design\", AVG(CASE WHEN LOWER(\"Attribute\") LIKE '%durability%' THEN \"Score\" ELSE NULL END) AS \"Durability\", AVG(CASE WHEN LOWER(\"Attribute\") LIKE '%price%' THEN \"Score\" ELSE NULL END) AS \"Price\" FROM processed_product_reviews3 WHERE \"ReviewTime\" IS NOT NULL GROUP BY 1 ORDER BY 1")
    
    return {"line": line, "pivot": pivot}

async def get_complaint_dashboard_data() -> dict:
    """Queries complaints table ONLY"""
    print("--- Fetching Complaint Data ---")
    
    cat = await run_sql_query('SELECT predicted_category, COUNT(*) as count FROM complaints GROUP BY 1 ORDER BY 2 DESC')
    ints = await run_sql_query('SELECT predicted_intensity_label, COUNT(*) as count FROM complaints GROUP BY 1 ORDER BY 2 DESC')
    top = await run_sql_query('SELECT predicted_category as "Category", complaint_text as "Issue", predicted_intensity_label as "Severity" FROM complaints ORDER BY prediction_timestamp DESC LIMIT 5')
    mat = await run_sql_query('SELECT predicted_category, predicted_intensity_label, COUNT(*) as count FROM complaints GROUP BY 1, 2 ORDER BY 1, 2')
    
    total = sum(x['count'] for x in cat) if cat else 0
    
    return {"total": total, "cat_dist": cat, "int_dist": ints, "top": top, "matrix": mat}

# --- 6. PROMPT TEMPLATES ---
SOCIAL_PAGE1_PROMPT = """System: Senior Product Manager. Analyze Social Data (Raw Reviews + Formatted Data): Total: {total}, Pie: {pie}, Bar: {bar}, Age: {age}, Scatter: {scatter}, Matrix: {matrix}. Task: 3 Key Insights."""
SOCIAL_PAGE2_PROMPT = """System: Customer Experience Manager. Analyze: Reviews: {total}, Text: {text}, Perf: {perf}. Task: Key Insights linking feedback to performance."""
TREND_PAGE1_PROMPT = """System: Market Trend Analyst. Analyze the monthly sentiment trends data provided. Task: Identify seasonal trends, anomalies, and patterns. Provide 2-3 key insights with actionable recommendations."""
TREND_PAGE2_PROMPT = """System: Strategic Analyst. Analyze the quarterly performance data provided. Task: Identify trajectory changes, attribute performance gaps, and strategic opportunities. Provide 2-3 key insights."""
COMPLAINT_PROMPT = """System: Senior CX Manager. Analyze Complaints Data: {top}, {matrix}. Task: Identify Critical Clusters."""

# --- 7. ENDPOINTS ---

@app.get("/api/health")
async def health():
    try:
        async with AsyncSessionLocal() as session: await session.execute(text("SELECT 1"))
        return {"status": "healthy", "db": "connected"}
    except Exception as e: return {"status": "unhealthy", "error": str(e)}

@app.get("/api/tables", response_model=List[dict])
async def get_tables():
    return [{"display_name": k, "id": v} for k, v in AVAILABLE_TABLES.items()]

@app.post("/api/chat", response_model=ChatResponse)
async def chat_handler(request: ChatRequest):
    prompt = request.prompt
    analyzer_model = get_gemini_analyzer()
    if not analyzer_model: return ChatResponse(error="Gemini API Key missing")
    
    try:
        # Step 1: Table Selection (Improved Router with detailed descriptions)
        table_prompt = f"""Analyze this question: "{prompt}"
        Available tables:
        1. processed_product_reviews3 - For product reviews and feedback
        2. Formatted_Review_dataset - For detailed review analysis
        3. complaints - For customer complaints data
        
        Which table should be used? Respond with ONLY the table name. If unsure, choose the most relevant table."""
        
        table_resp = analyzer_model.generate_content(table_prompt)
        table_to_query = table_resp.text.strip().lower().replace('"', '').replace("'", "")
        
        # Map response to actual table name
        found_table = "processed_product_reviews3"  # Default
        if "product" in table_to_query or "review" in table_to_query:
            found_table = "processed_product_reviews3"
        elif "format" in table_to_query:
            found_table = "Formatted_Review_dataset"
        elif "complaint" in table_to_query:
            found_table = "complaints"
        
        # Validate table exists in schema
        if found_table not in TABLE_SCHEMAS and f'"{found_table}"' not in TABLE_SCHEMAS:
            found_table = "processed_product_reviews3"  # Fallback
        
        # Step 2: Intent Classification
        intent_resp = analyzer_model.generate_content(f"Classify the user's question as 'data_query' or 'general_question'. User Question: \"{prompt}\". Respond with only the category name.")
        intent = intent_resp.text.strip()

        if "general" in intent.lower():
            return ChatResponse(
                insights="I'm sorry, I can only answer questions related to our product reviews and complaint data. Please ask a question about that topic."
            )

        # Step 3: SQL Generation with enhanced rules
        schema = get_table_schema(found_table)
        
        # Special handling for delivery vs returns queries
        if "complaints" in found_table and any(x in prompt.lower() for x in ['delivery', 'return']):
            generated_sql = f"""SELECT COUNT(*) FILTER (WHERE predicted_category ILIKE '%delivery%') AS delivery_complaints, COUNT(*) FILTER (WHERE predicted_category ILIKE '%return%') AS returns_complaints FROM complaints"""
        else:
            # Build table-specific SQL generation prompt
            if found_table == "processed_product_reviews3":
                table_rules = """
- Table: processed_product_reviews3
- Key columns: "Category" (product category), "Attribute" (product feature), "Score" (rating), "Reason" (review text), "reviewerID", "ReviewTime" (TIMESTAMP)
- For text search about features (e.g., color, design, quality): Use WHERE LOWER("Reason") LIKE '%keyword%'
- For category grouping: Use GROUP BY "Category"
- For counting: Use COUNT(*) AS count
- For date grouping (month/year): Cast EXTRACT results to integers to avoid decimals: CAST(EXTRACT(YEAR FROM "ReviewTime") AS INTEGER), CAST(EXTRACT(MONTH FROM "ReviewTime") AS INTEGER)
- Example for month/year: SELECT CAST(EXTRACT(YEAR FROM "ReviewTime") AS INTEGER) AS year, CAST(EXTRACT(MONTH FROM "ReviewTime") AS INTEGER) AS month, "Attribute", COUNT(*) AS count FROM "processed_product_reviews3" GROUP BY CAST(EXTRACT(YEAR FROM "ReviewTime") AS INTEGER), CAST(EXTRACT(MONTH FROM "ReviewTime") AS INTEGER), "Attribute" ORDER BY year, month, "Attribute"
- IMPORTANT: When searching for words with spelling variations (e.g., color vs colour), search for both: LOWER("Reason") LIKE '%color%' OR LOWER("Reason") LIKE '%colour%'
"""
            elif found_table == "Formatted_Review_dataset":
                table_rules = """
- Table: Formatted_Review_dataset
- Key columns: "Review_id", "Attribute" (product feature), "Score" (rating), "Reason" (review text)
- For text search: Use WHERE LOWER("Reason") LIKE '%keyword%'
- For grouping by attributes: Use GROUP BY "Attribute"
- For counting by attribute: SELECT "Attribute", COUNT(*) AS count FROM "Formatted_Review_dataset" GROUP BY "Attribute"
- IMPORTANT: When searching for words with spelling variations, search for both spellings
"""
            elif found_table == "complaints":
                table_rules = """
- Table: complaints
- Key columns: complaint_text (review text), predicted_category, predicted_intensity_label, predicted_intensity_score, prediction_timestamp (TIMESTAMP)
- For text search: Use WHERE LOWER(complaint_text) LIKE '%keyword%'
- For category analysis: Use GROUP BY predicted_category
- For date grouping: Cast EXTRACT results to integers: CAST(EXTRACT(YEAR FROM prediction_timestamp) AS INTEGER), CAST(EXTRACT(MONTH FROM prediction_timestamp) AS INTEGER)
- IMPORTANT: When searching for words with spelling variations, search for both spellings
"""
            else:
                table_rules = f"- Table: {found_table}\n- Schema: {schema}"
            
            system_prompt = f"""You are a Postgres Expert. Create a valid SQL query.
{table_rules}

CRITICAL RULES:
1. For case-insensitive string matching, use LOWER() on both column and search value.
   Example: WHERE LOWER("Reason") LIKE '%color%' OR LOWER("Reason") LIKE '%colour%'
2. For keyword search in text columns, use LIKE with wildcards: '%keyword%'
3. Always alias calculated columns with AS. Example: COUNT(*) AS count, CAST(EXTRACT(YEAR FROM "ReviewTime") AS INTEGER) AS year
4. When searching for variations of a word (e.g., color/colour, analyze/analyse), check ALL common spellings.
5. For grouping with counts, always include the grouping columns in SELECT and GROUP BY.
6. For date/time queries, ALWAYS cast EXTRACT results to INTEGER to avoid decimals: CAST(EXTRACT(YEAR FROM column) AS INTEGER)
7. When grouping by multiple columns (year, month, attribute), include all in SELECT, GROUP BY, and ORDER BY using the CAST version.
8. ONLY output the SQL query. No explanations. If impossible, respond with 'ERROR'.
"""
            sql_resp = analyzer_model.generate_content(f"{system_prompt}\nQuestion: {prompt}")
            generated_sql = clean_sql_query(sql_resp.text)
        
        if not generated_sql or "ERROR" in generated_sql or not generated_sql.lower().startswith("select"):
            # Provide helpful error message
            error_msg = "I was unable to generate a valid query. Try rephrasing by:\n"
            if "month" in prompt.lower() or "year" in prompt.lower():
                error_msg += "- Using simpler date references (e.g., 'by date' or 'over time')\n"
            if "aggregate" in prompt.lower() or "sum" in prompt.lower():
                error_msg += "- Breaking down the aggregation request into simpler parts\n"
            error_msg += "- Specifying exactly which columns you want to group or filter by"
            print(f"--- SQL GENERATION FAILED ---")
            print(f"Question: {prompt}")
            print(f"Table: {found_table}")
            print(f"Generated SQL: {generated_sql}")
            print(f"--- END ERROR ---")
            return ChatResponse(error=error_msg)
        
        # Step 4: Execute Query
        results = await run_sql_query(generated_sql)
        
        # Debug logging
        print(f"--- DEBUG INFO ---")
        print(f"Question: {prompt}")
        print(f"Selected Table: {found_table}")
        print(f"Generated SQL: {generated_sql}")
        print(f"Results Found: {len(results) if results else 0}")
        print(f"--- END DEBUG ---")
        
        if not results:
            return ChatResponse(insights=f"The query ran successfully, but returned no results.\n\nThis could mean:\n1. No data matches your search criteria\n2. The keyword might be spelled differently in the database\n3. Try searching for related terms\n\n**Debug Info:** Table: {found_table}")

        
        # Step 5: Format Results
        html_table = format_results_to_html(results)
        results_str = format_results_to_string(results[:10])
        
        # Step 6: Generate AI Insights
        insights_prompt = f"""You are a helpful data analyst assistant.

The user asked: "{prompt}"

The database returned: {results_str}

Schema of {found_table}: {schema}

Provide:
1. **Insight & Recommendation:** One concise insight with an actionable recommendation.
2. Two newlines.
3. **Suggested Questions:** Three simple follow-up questions as bullets.

CRITICAL: Questions must only use columns from the schema and be answerable with simple SQL."""
        
        insights_resp = analyzer_model.generate_content(insights_prompt)
        
        return ChatResponse(results_html=html_table, insights=clean_gemini_response(insights_resp.text))
        
    except Exception as e:
        print(f"Chat handler error: {str(e)}")
        return ChatResponse(error=f"An unexpected error occurred: {str(e)}")

@app.post("/api/get-social-insights", response_model=InsightResponse)
async def social_insights(req: InsightRequest):
    try:
        d = await get_social_dashboard_data()
        model = get_gemini_analyzer()
        r1 = model.generate_content(SOCIAL_PAGE1_PROMPT.format(total=d['page1']['total'], pie=json.dumps(d['page1']['pie'], default=str), bar=json.dumps(d['page1']['bar'], default=str), age=json.dumps(d['page1']['age'], default=str), scatter=json.dumps(d['page1']['scatter'], default=str), matrix=json.dumps(d['page1']['matrix'], default=str)))
        r2 = model.generate_content(SOCIAL_PAGE2_PROMPT.format(total=d['page2']['total'], text=json.dumps(d['page2']['text'], default=str), perf=json.dumps(d['page2']['perf'], default=str)))
        return InsightResponse(insights=f"**Page 1:**\n{clean_gemini_response(r1.text)}\n\n---\n\n**Page 2:**\n{clean_gemini_response(r2.text)}")
    except Exception as e: return InsightResponse(error=str(e))

@app.post("/api/get-trend-insights", response_model=InsightResponse)
@app.post("/api/get-trend-insights", response_model=InsightResponse)
async def trend_insights(req: InsightRequest):
    try:
        d = await get_trend_dashboard_data()
        model = get_gemini_analyzer()
        
        # Format data as readable text for LLM, not raw JSON
        line_text = format_results_to_string(d['line']) if d['line'] else "No data available"
        pivot_text = format_results_to_string(d['pivot']) if d['pivot'] else "No data available"
        
        prompt1 = f"""{TREND_PAGE1_PROMPT}

Monthly Sentiment Trends Data:
{line_text}

Provide analysis starting with key insights."""
        
        prompt2 = f"""{TREND_PAGE2_PROMPT}

Quarterly Performance Data:
{pivot_text}

Provide analysis starting with key insights."""
        
        r1 = model.generate_content(prompt1)
        r2 = model.generate_content(prompt2)
        
        return InsightResponse(insights=f"**Monthly:**\n{clean_gemini_response(r1.text)}\n\n---\n\n**Quarterly:**\n{clean_gemini_response(r2.text)}")
    except Exception as e: return InsightResponse(error=str(e))

@app.post("/api/get-complaint-insights", response_model=InsightResponse)
async def complaint_insights(req: InsightRequest):
    try:
        d = await get_complaint_dashboard_data()
        model = get_gemini_analyzer()
        resp = model.generate_content(COMPLAINT_PROMPT.format(total=d['total'], cat_dist=json.dumps(d['cat_dist'], default=str), int_dist=json.dumps(d['int_dist'], default=str), top=json.dumps(d['top'], default=str), matrix=json.dumps(d['matrix'], default=str)))
        return InsightResponse(insights=clean_gemini_response(resp.text))
    except Exception as e: return InsightResponse(error=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)