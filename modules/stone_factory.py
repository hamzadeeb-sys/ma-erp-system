import streamlit as st
import pandas as pd
from datetime import datetime
from core.db import run_query, get_db_cursor
from core.utils import to_excel_download_link, get_next_invoice_id

def render_stone_factory():
    st.subheader("🏭 منظومة وحسابات معمل الحجر الصناعي (شراكة مستقلة)")
    st.caption("عقد المشاركة: حصة المعمل (أحمد شيخ) 75% | حصة الشركة (مصعب المصري) 25% | زكاة 2% تُحسم أولاً")

    with get_db_cursor() as (cur, _):
        cur.execute("SELECT id FROM projects WHERE name = 'معمل الحجر الصناعي';")
        f_proj = cur.fetchone()
        factory_proj_id = int(f_proj[0]) if f_proj else 1

        cur.execute("SELECT id FROM vaults WHERE name = 'صندوق معمل الحجر (USD)';")
        v_usd = cur.fetchone()
        v_usd_id = int(v_usd[0]) if v_usd else 3

        cur.execute("SELECT id FROM vaults WHERE name = 'صندوق معمل الحجر (SYP)';")
        v_syp = cur.fetchone()
        v_syp_id = int(v_syp[0]) if v_syp else 4

        cur.execute("SELECT COALESCE(SUM(CASE WHEN direction = 'IN' THEN amount ELSE -amount END), 0) FROM transactions WHERE vault_id = %s;", (v_usd_id,))
        fac_bal_usd = float(cur.fetchone()[0] or 0.0)

        cur.execute("SELECT COALESCE(SUM(CASE WHEN direction = 'IN' THEN amount ELSE -amount END), 0) FROM transactions WHERE vault_id = %s;", (v_syp_id,))
        fac_bal_syp = float(cur.fetchone()[0] or 0.0)

        cur.execute("SELECT COALESCE(SUM(amount_usd), 0) FROM transactions WHERE project_id = %s AND direction = 'IN';", (factory_proj_id,))
        fac_total_revenue = float(cur.fetchone()[0] or 0.0)

        cur.execute("SELECT COALESCE(SUM(amount_usd), 0) FROM transactions WHERE project_id = %s AND direction = 'OUT' AND tx_type != 'توزيع أرباح شريك';", (factory_proj_id,))
        fac_total_expenses = float(cur.fetchone()[0] or 0.0)

        cur.execute("""
            SELECT COALESCE(SUM(t.amount_usd), 0)
            FROM transactions t
            JOIN stakeholders s ON t.stakeholder_id = s.id
            WHERE t.project_id = %s AND s.name LIKE %s AND t.tx_type IN ('توزيع أرباح شريك', 'راتب او سلفة');
        """, (factory_proj_id, '%أحمد شيخ%'))
        ahmed_withdrawals = float(cur.fetchone()[0] or 0.0)

        cur.execute("""
            SELECT COALESCE(SUM(t.amount_usd), 0)
            FROM transactions t
            JOIN stakeholders s ON t.stakeholder_id = s.id
            WHERE t.project_id = %s AND s.name LIKE %s AND t.tx_type IN ('توزيع أرباح شريك', 'راتب او سلفة');
        """, (factory_proj_id, '%مصعب%'))
        mosab_withdrawals = float(cur.fetchone()[0] or 0.0)

    gross_factory_profit = fac_total_revenue - fac_total_expenses
    zakat_deduction = (gross_factory_profit * 0.02) if gross_factory_profit > 0 else 0.0
    net_distributable = gross_factory_profit - zakat_deduction if gross_factory_profit > 0 else 0.0

    ahmed_share_75 = net_distributable * 0.75
    company_share_25 = net_distributable * 0.25
    ahmed_net_payable = ahmed_share_75 - ahmed_withdrawals
    company_net_payable = company_share_25 - mosab_withdrawals

    tab_dash, tab_settle, tab_tx, tab_new = st.tabs([
        "📊 أرصدة وسيولة المعمل", 
        "🤝 تصفية الأرباح العقدية", 
        "📑 سجل حركات المعمل", 
        "➕ إضافة حركة جديدة"
    ])

    with tab_dash:
        cf1, cf2 = st.columns(2)
        with cf1:
            st.markdown(f'<div class="metric-card"><div class="metric-title">صندوق المعمل (USD)</div><div class="metric-value-usd">{fac_bal_usd:,.2f} $</div></div>', unsafe_allow_html=True)
        with cf2:
            st.markdown(f'<div class="metric-card" style="border-top-color: #BE9D5F;"><div class="metric-title">صندوق المعمل (SYP)</div><div class="metric-value-gold">{fac_bal_syp:,.0f} ل.س</div></div>', unsafe_allow_html=True)

        st.markdown("---")
        cs1, cs2, cs3, cs4 = st.columns(4)
        with cs1: st.metric("المقبوضات الإجمالية", f"{fac_total_revenue:,.2f} $")
        with cs2: st.metric("المصاريف التشغيلية", f"{fac_total_expenses:,.2f} $")
        with cs3: st.metric("الربح الإجمالي", f"{gross_factory_profit:,.2f} $")
        with cs4: st.metric("مخصص الزكاة (2%)", f"{zakat_deduction:,.2f} $")

    with tab_settle:
        settle_data = [
            {"الطرف": "أحمد شيخ (المعمل)", "النسبة": "75%", "الأرباح المستحقة ($)": f"{ahmed_share_75:,.2f} $", "المسحوبات السابقة": f"{ahmed_withdrawals:,.2f} $", "الصافي المتبقي": f"{ahmed_net_payable:,.2f} $"},
            {"الطرف": "مصعب المصري / شركة MA", "النسبة": "25%", "الأرباح المستحقة ($)": f"{company_share_25:,.2f} $", "المسحوبات السابقة": f"{mosab_withdrawals:,.2f} $", "الصافي المتبقي": f"{company_net_payable:,.2f} $"},
            {"الطرف": "أمانة الزكاة (بيد أحمد شيخ)", "النسبة": "2% مقطوعة", "الأرباح المستحقة ($)": f"{zakat_deduction:,.2f} $", "المسحوبات السابقة": "0.00 $", "الصافي المتبقي": f"{zakat_deduction:,.2f} $"}
        ]
        st.dataframe(pd.DataFrame(settle_data), use_container_width=True, hide_index=True)

    with tab_tx:
        df_fac_txs = run_query("""
            SELECT t.id AS "رقم الفاتورة", t.tx_date AS "التاريخ", t.tx_type AS "نوع الحركة",
                   COALESCE(s.name, 'عام') AS "الطرف المرتبط", t.amount AS "المبلغ",
                   CASE WHEN t.currency = 'USD' THEN 'دولار ($)' ELSE 'ليرة سورية' END AS "العملة",
                   t.amount_usd AS "المعادل بالدولار ($)",
                   CASE WHEN t.direction = 'IN' THEN 'وارد (قبض)' ELSE 'صادر (صرف)' END AS "الاتجاه",
                   t.payment_method AS "طريقة الدفع", t.description AS "البيان"
            FROM transactions t
            LEFT JOIN stakeholders s ON t.stakeholder_id = s.id
            WHERE t.project_id = %s
            ORDER BY t.tx_date DESC, t.id DESC;
        """, (factory_proj_id,))
        if not df_fac_txs.empty:
            st.dataframe(df_fac_txs.fillna("-"), use_container_width=True, hide_index=True)
            st.download_button("📥 تصدير سجل المعمل (Excel)", data=to_excel_download_link(df_fac_txs, "Factory_Stone.xlsx"), file_name="Factory_Stone.xlsx")
        else:
            st.info("لا توجد حركات مسجلة لمعمل الحجر.")

    with tab_new:
        all_stk_fac = run_query("SELECT id, name FROM stakeholders ORDER BY name;")
        auto_fac_id = get_next_invoice_id()

        with st.form("add_fac_tx_form", clear_on_submit=True):
            cf_1, cf_2, cf_3 = st.columns(3)
            with cf_1:
                f_inv_id = st.text_input("رقم السند", value=auto_fac_id)
                f_date = st.date_input("التاريخ", datetime.now().date())
                f_type = st.selectbox("نوع الحركة", ["شراء مواد أولية للمعمل", "مبيعات حجر (قبض من عميل)", "أجور عمال المعمل", "مصاريف ونقل وهدر", "توزيع أرباح شريك (سحب شخصي)", "سداد زكاة"])
            with cf_2:
                f_stk = st.selectbox("الطرف / المورد / العميل", all_stk_fac['name'].tolist())
                f_method = st.selectbox("طريقة الدفع", ["كاش من صندوق المعمل", "حوالة مصرفية", "شيك"])
            with cf_3:
                f_curr = st.selectbox("العملة", ["USD", "SYP"])
                f_rate = st.number_input("سعر الصرف", min_value=1.0, value=1.0 if f_curr == "USD" else 131.0)
                f_amt = st.number_input("المبلغ", min_value=0.0, step=50.0)

            f_desc = st.text_area("البيان والملاحظات التفصيلية")

            if st.form_submit_button("🚀 حفظ وترحيل الحركة"):
                if f_amt > 0:
                    s_id_val = int(all_stk_fac.loc[all_stk_fac['name'] == f_stk, 'id'].values[0])
                    v_target_id = v_usd_id if f_curr == 'USD' else v_syp_id
                    dir_m = 'IN' if any(k in f_type for k in ['مبيعات', 'قبض']) else 'OUT'
                    amt_u_val = float(f_amt if f_curr == 'USD' else (f_amt / f_rate))

                    with get_db_cursor(commit=True) as (cur, _):
                        cur.execute("""
                            INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """, (str(f_inv_id), f_date, str(f_type), factory_proj_id, s_id_val, v_target_id, float(f_amt), str(f_curr), float(f_rate), float(amt_u_val), str(dir_m), str(f_method), str(f_desc)))
                    st.success(f"تم ترحيل السند {f_inv_id} بنجاح.")
                    st.rerun()
