import io
import re
import pandas as pd
from core.db import get_db_cursor

def to_excel_download_link(df: pd.DataFrame, filename: str = "report.xlsx") -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.fillna("").to_excel(writer, index=False, sheet_name='التقرير المالي')
    return output.getvalue()

def get_next_invoice_id() -> str:
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT id FROM transactions WHERE id ~ '^PAY-[0-9]+' ORDER BY id DESC LIMIT 50;")
        rows = cur.fetchall()
        max_num = 0
        if rows:
            for r in rows:
                match = re.search(r'^PAY-(\d+)', str(r[0]))
                if match:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
        if max_num > 0:
            return f"PAY-{(max_num + 1):05d}"
        cur.execute("SELECT COUNT(*) FROM transactions;")
        cnt = cur.fetchone()[0]
        return f"PAY-{(cnt + 1):05d}"
