
import streamlit as st
from openai import OpenAI
import sqlite3
from datetime import datetime
import pandas as pd
import plotly.express as px

# Initialize OpenAI client with API key from Streamlit secrets
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="Trumpometer", layout="wide")
st.title("🇺🇸 Trumpometer v3.0 – Real-Time Market Sentiment from Trump Tweets")

# Connect or create SQLite DB
conn = sqlite3.connect("signals.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS signals (timestamp TEXT, tweet TEXT, sentiment TEXT, score REAL, topic TEXT, assets TEXT)")
conn.commit()

# Tweet input
st.subheader("Paste a Trump Tweet to Analyze")
tweet = st.text_area("Trump's Tweet Text", height=150)

if st.button("Analyze Tweet"):
    with st.spinner("Analyzing..."):
        prompt = f"""
You are Trumpometer, a financial sentiment analyst.

Analyze the following Trump tweet for market impact.

Tweet: "{tweet}"

Return a JSON object like this:
{{
  "trump_related": true,
  "market_relevance": true,
  "sentiment": "bullish" or "bearish" or "neutral",
  "confidence_score": float (-2 to +2),
  "topic": "economy/geopolitics/etc.",
  "related_assets": ["USD", "Oil", "S&P 500"]
}}

Only return the JSON object.
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a financial sentiment extraction agent."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            result = response.choices[0].message.content
            st.code(result, language="json")

            # Save to database
            now = datetime.utcnow().isoformat()
            import json
            data = json.loads(result)
            c.execute("INSERT INTO signals VALUES (?, ?, ?, ?, ?, ?)",
                      (now, tweet, data["sentiment"], data["confidence_score"], data["topic"], ", ".join(data["related_assets"])))
            conn.commit()
        except Exception as e:
            st.error(f"Failed to analyze tweet: {str(e)}")

# Display stored signals
st.subheader("📈 Sentiment Trend (Last 10 Tweets)")
df = pd.read_sql_query("SELECT * FROM signals ORDER BY timestamp DESC LIMIT 10", conn)

if not df.empty:
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    fig = px.line(df.sort_values("timestamp"), x="timestamp", y="score", title="Trump Tweet Sentiment Score Over Time")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df)
else:
    st.info("No data yet. Submit a tweet above to generate sentiment.")
