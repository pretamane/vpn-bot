import streamlit as st
import sqlite3
import pandas as pd
import os

DB_PATH = "src/db/vpn_bot.db"

st.set_page_config(page_title="VPN Bot Dashboard", layout="wide")

st.title("VPN Bot Dashboard")

if not os.path.exists(DB_PATH):
    st.error(f"Database not found at {DB_PATH}")
else:
    conn = sqlite3.connect(DB_PATH)
    
    st.header("Users")
    try:
        users_df = pd.read_sql_query("SELECT * FROM users ORDER BY created_at DESC", conn)
        st.dataframe(users_df)
    except Exception as e:
        st.error(f"Error reading users: {e}")

    st.header("Payment Transactions")
    try:
        payments_df = pd.read_sql_query("SELECT * FROM payment_transactions ORDER BY created_at DESC", conn)
        st.dataframe(payments_df)
    except Exception as e:
        st.error(f"Error reading payments: {e}")

    st.header("Usage Logs")
    try:
        usage_df = pd.read_sql_query("SELECT * FROM usage_logs ORDER BY date DESC", conn)
        st.dataframe(usage_df)
    except Exception as e:
        st.error(f"Error reading usage: {e}")

    st.header("Custom Query")
    query = st.text_area("Enter SQL Query", "SELECT * FROM users")
    if st.button("Run Query"):
        try:
            query_df = pd.read_sql_query(query, conn)
            st.dataframe(query_df)
        except Exception as e:
            st.error(f"Query Error: {e}")

    conn.close()
