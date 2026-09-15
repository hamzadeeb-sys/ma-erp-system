import streamlit as st
import psycopg2
from psycopg2 import pool
import psycopg2.extensions
import numpy as np
import pandas as pd
from contextlib import contextmanager

# تسجيل مهايئات NumPy
psycopg2.extensions.register_adapter(np.float64, lambda val: psycopg2.extensions.Float(float(val)))
psycopg2.extensions.register_adapter(np.float32, lambda val: psycopg2.extensions.Float(float(val)))
psycopg2.extensions.register_adapter(np.int64, lambda val: psycopg2.extensions.AsIs(int(val)))
psycopg2.extensions.register_adapter(np.int32, lambda val: psycopg2.extensions.AsIs(int(val)))

@st.cache_resource
def get_db_pool():
    if "postgres" not in st.secrets:
        st.error("⚠️ لم يتم العثور على إعدادات [postgres] في Secrets السيرفر.")
        st.stop()
    cfg = st.secrets["postgres"]
    try:
        return pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host=cfg["host"],
            port=int(cfg["port"]),
            dbname=cfg["dbname"],
            user=cfg["user"],
            password=cfg["password"],
            sslmode="require",
            connect_timeout=10
        )
    except Exception as e:
        st.error(f"❌ خطأ اتصال مباشر بقاعدة البيانات: {e}")
        st.stop()

@contextmanager
def get_db_cursor(commit=False):
    db_pool = get_db_pool()
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            yield cur, conn
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        db_pool.putconn(conn)

def run_query(query: str, params: tuple = None) -> pd.DataFrame:
    with get_db_cursor() as (cur, conn):
        return pd.read_sql(query, conn, params=params)
