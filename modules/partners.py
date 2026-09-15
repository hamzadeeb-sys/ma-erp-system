import streamlit as st
import pandas as pd
from core.db import run_query, get_db_cursor

def render_partners(current_user):
    st.subheader("🤝 هيكل الملكية وحساب حصص الشركاء وأرباح الإدارة")
    with get_db_cursor() as (cur, _):
        cur.execute("""
            SELECT COALESCE(SUM(ROUND(t.amount_usd * p.management_fee_rate, 2)), 0)
            FROM projects p JOIN transactions t ON p.id = t.project_id
            WHERE t.direction = 'OUT' AND p.project_type NOT IN ('Internal', 'Factory');
        """)
        total_company_profit = float(cur.fetchone()[0] or 0.0)

        cur.execute("SELECT partner_equity_pct, salary_amount, salary_currency FROM stakeholders WHERE name = 'حمزة ديب';")
        h_data = cur.fetchone()
        hamza_pct = float(h_data[0]) if (h_data and h_data[0] is not None and float(h_data[0]) > 0) else 15.00
        hamza_sal = float(h_data[1]) if h_data and h_data[1] is not None else 0.00
        hamza_sal_curr = h_data[2] if h_data and h_data[2] else 'USD'

        cur.execute("""
            SELECT COALESCE(SUM(amount_usd), 0) FROM transactions t
            LEFT JOIN stakeholders s ON t.stakeholder_id = s.id
            WHERE (s.name = 'مصعب المصري' OR t.description LIKE '%مصعب%')
              AND t.tx_type IN ('ايراد عام', 'مصروف عام') AND t.description LIKE '%راس مال%';
        """)
        mosab_capital = float(cur.fetchone()[0] or 11435.00)

        cur.execute("""
            SELECT COALESCE(SUM(amount_usd), 0) FROM transactions t
            LEFT JOIN stakeholders s ON t.stakeholder_id = s.id
            WHERE (s.name = 'سامر ديب' OR t.description LIKE '%سامر%') AND t.tx_type = 'ايراد عام';
        """)
        samer_capital = float(cur.fetchone()[0] or 1814.00)

    total_financial_capital = mosab_capital + samer_capital
    remaining_equity = max(0.0, 100.0 - hamza_pct)
    mosab_pct = (mosab_capital / total_financial_capital * remaining_equity) if total_financial_capital > 0 else remaining_equity
    samer_pct = (samer_capital / total_financial_capital * remaining_equity) if total_financial_capital > 0 else 0.0

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="metric-card"><div class="metric-title">رأس المال التأسيسي الإجمالي</div><div class="metric-value-usd">{total_financial_capital:,.2f} $</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><div class="metric-title">أتعاب الإدارة المتراكمة</div><div class="metric-value-gold">{total_company_profit:,.2f} $</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><div class="metric-title">حصة حمزة ديب الإدارية</div><div class="metric-value-usd" style="color: #BE9D5F;">{hamza_pct:.2f}%</div></div>', unsafe_allow_html=True)

    partners_breakdown = [
        {"الشريك": "مصعب المصري", "الصفة": "مؤسس وشريك مالي وإداري", "المساهمة": f"{mosab_capital:,.2f} $", "نسبة رأس المال": f"{(mosab_capital/total_financial_capital*100 if total_financial_capital else 0):.1f}%", "نسبة الملكية": f"{mosab_pct:.2f}%", "الأرباح المستحقة": f"{(total_company_profit * mosab_pct / 100.0):,.2f} $"},
        {"الشريك": "سامر ديب", "الصفة": "مساهم وشريك مالي", "المساهمة": f"{samer_capital:,.2f} $", "نسبة رأس المال": f"{(samer_capital/total_financial_capital*100 if total_financial_capital else 0):.1f}%", "نسبة الملكية": f"{samer_pct:.2f}%", "الأرباح المستحقة": f"{(total_company_profit * samer_pct / 100.0):,.2f} $"},
        {"الشريك": "حمزة ديب", "الصفة": "شريك إداري ومسؤول تقني", "المساهمة": "0.00 $", "نسبة رأس المال": "0.0%", "نسبة الملكية": f"{hamza_pct:.2f}%", "الأرباح المستحقة": f"{(total_company_profit * hamza_pct / 100.0):,.2f} $"}
    ]
    st.dataframe(pd.DataFrame(partners_breakdown), use_container_width=True, hide_index=True)

    if current_user['role'] == "Admin":
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### ⚙️ تحديث نسبة وراتب حمزة ديب")
        with st.form("update_hamza_form"):
            col_h1, col_h2, col_h3 = st.columns(3)
            with col_h1: new_h_pct = st.number_input("النسبة % من الأرباح", min_value=1.0, max_value=50.0, value=float(hamza_pct), step=1.0)
            with col_h2: new_h_sal = st.number_input("الراتب الشهري الثابت", min_value=0.0, value=float(hamza_sal), step=50.0)
            with col_h3:
                new_h_curr_choice = st.selectbox("عملة الراتب", ["USD", "SYP"], index=0 if hamza_sal_curr == "USD" else 1)
            if st.form_submit_button("💾 حفظ التعديلات"):
                with get_db_cursor(commit=True) as (cur, _):
                    cur.execute("UPDATE stakeholders SET partner_equity_pct = %s, salary_amount = %s, salary_currency = %s WHERE name = 'حمزة ديب';", (new_h_pct, new_h_sal, new_h_curr_choice))
                st.success("تم تحديث البيانات بنجاح.")
                st.rerun()
