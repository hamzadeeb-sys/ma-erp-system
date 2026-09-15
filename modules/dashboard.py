import streamlit as st
import pandas as pd
from core.db import run_query

def render_dashboard():
    st.subheader("💵 السيولة النقدية وأرصدة صناديق الشركة العامة")
    df_vaults = run_query("""
        SELECT v.name AS vault_name, v.currency,
               COALESCE(SUM(CASE WHEN t.direction = 'IN' THEN t.amount ELSE -t.amount END), 0) AS current_balance
        FROM vaults v 
        LEFT JOIN transactions t ON v.id = t.vault_id 
        WHERE v.name NOT LIKE '%معمل الحجر%'
        GROUP BY v.id, v.name, v.currency;
    """)
    col1, col2 = st.columns(2)
    with col1:
        usd_bal = df_vaults.loc[df_vaults['currency'] == 'USD', 'current_balance'].values[0] if not df_vaults.empty else 0
        st.markdown(f'<div class="metric-card"><div class="metric-title">رصيد الصندوق الرئيسي (USD)</div><div class="metric-value-usd">{usd_bal:,.2f} $</div></div>', unsafe_allow_html=True)
    with col2:
        syp_bal = df_vaults.loc[df_vaults['currency'] == 'SYP', 'current_balance'].values[0] if not df_vaults.empty else 0
        st.markdown(f'<div class="metric-card"><div class="metric-title">رصيد الصندوق الرئيسي (SYP)</div><div class="metric-value-gold">{syp_bal:,.0f} ل.س</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🏗️ أداء المشاريع النشطة والتشغيلية")
    df_proj_summary = run_query("""
        SELECT p.name AS "المشروع",
               CASE WHEN p.project_type = 'Finishing' THEN 'إكساء وتشطيب'
                    WHEN p.project_type = 'Development' THEN 'تطوير عقاري'
                    WHEN p.project_type = 'Internal' THEN 'داخلي ومخزون'
                    ELSE COALESCE(p.project_type, 'عام') END AS "نوع المشروع",
               CASE WHEN p.status = 'Active' THEN 'نشط 🟢' ELSE 'مكتمل 🏁' END AS "الحالة",
               COUNT(t.id) AS "عدد العمليات",
               COALESCE(SUM(CASE WHEN t.direction = 'OUT' THEN t.amount_usd ELSE 0 END), 0) AS "إجمالي المصاريف ($)",
               COALESCE(SUM(CASE WHEN t.direction = 'IN' THEN t.amount_usd ELSE 0 END), 0) AS "إجمالي المقبوضات ($)"
        FROM projects p 
        LEFT JOIN transactions t ON p.id = t.project_id 
        WHERE p.project_type != 'Factory'
        GROUP BY p.id, p.name, p.project_type, p.status;
    """)
    st.dataframe(df_proj_summary.fillna("-"), use_container_width=True, hide_index=True)
