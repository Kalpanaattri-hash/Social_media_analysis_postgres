# Social Media & Product Review Analysis Chatbot

This project is an AI-powered analytics dashboard and chatbot designed to analyze social media comments and product reviews (e.g., Amazon reviews). It leverages **PostgreSQL** for robust data storage, **FastAPI** for a high-performance backend, and **Microsoft Power BI** for advanced visualization.

## 🚀 Features

* **Interactive Chatbot:** Ask questions about your data in plain English using a React-based chat interface.
* **Sentiment Analysis:** Automatically categorizes reviews as Positive, Negative, or Neutral using GenAI.
* **Power BI Integration:** Interactive dashboards to visualize KPI trends, sentiment distribution, and complaint hotspots.
* **FastAPI Backend:** High-speed, asynchronous API to handle requests and database queries efficiently.
* **GenAI Powered:** Uses Google Gemini (or similar LLMs) to generate human-like summaries and answers.

## 🛠️ Tech Stack

* **Frontend:** React.js, Vite
* **Backend:** Python (FastAPI)
* **Database:** PostgreSQL
* **Visualization:** Microsoft Power BI
* **AI/ML:** Google Gemini API / OpenAI (for RAG and Chatbot logic)
* **Data Processing:** Pandas, NumPy, Psycopg2, SQLAlchemy

## 📂 Project Structure

```bash
├── public/                 # Static assets
├── src/                    # React Frontend logic
│   ├── assets/
│   ├── components/         # Chatbot & Dashboard components
│   ├── App.jsx             # Main Frontend Entry
│   └── main.jsx
├── main.py                 # FastAPI Application Entry Point
├── requirements.txt        # Python dependencies
├── Service_account.json    # Google AI Credentials (NOT UPLOADED)
├── .env                    # Environment variables (DB Creds & API Keys)
└── amazon_reviews.csv      # Sample dataset
⚙️ Setup & Installation
1. Clone the Repository
Bash

git clone [https://github.com/Kalpanaattri-hash/Social_media_analysis_bigquery.git](https://github.com/Kalpanaattri-hash/Social_media_analysis_bigquery.git)
cd Social_media_analysis_bigquery
2. Backend Setup (FastAPI)
Bash

# Create virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
3. Database Setup (PostgreSQL)
Ensure PostgreSQL is installed and running.

Create a database named reviews_db.

Update the connection string in your code or .env file.

4. Configuration
Create a .env file in the root directory:

Code snippet

# AI API Key
GOOGLE_API_KEY=your_gemini_api_key

# PostgreSQL Credentials
DB_URL=postgresql://user:password@localhost:5432/reviews_db
5. Frontend Setup (React)
Bash

# Install Node modules
npm install

# Start the development server
npm run dev
📊 Power BI Setup
Open Power BI Desktop.

Click Get Data -> PostgreSQL Database.

Enter your Server (e.g., localhost) and Database name (reviews_db).

Load the data to build your custom dashboard for Sentiment Trends and Topic Analysis.

🚀 Usage
Start the FastAPI Backend:

Bash

# Run using uvicorn (Standard for FastAPI)
uvicorn main:app --reload
(Or if your main.py is configured to run directly: python main.py)

Start the React Frontend:

Bash

npm run dev
Interact:

Chatbot: Open http://localhost:5173

API Docs: Open http://127.0.0.1:8000/docs (Swagger UI provided by FastAPI)

🛡️ Security Note
This repository does not contain the .env file or Service_account.json. These files are excluded via .gitignore to protect sensitive API keys and database passwords
