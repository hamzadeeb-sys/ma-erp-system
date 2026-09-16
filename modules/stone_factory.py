import streamlit as st
import pandas as pd
from datetime import datetime
from core.db import run_query, get_db_cursor
from core.utils import to_excel_download_link, get_next_invoice_id

def render_stone_factory():
    st.subheader(":material/precision_manufacturing: منظومة وحسابات معمل الحجر الصناعي (شراكة مستقلة)")
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

        cur.execute("""
            SELECT COALESCE(SUM(amount_usd), 0) 
            FROM transactions 
            WHERE project_id = %s AND direction = 'IN' AND settlement_id IS NULL;
        """, (factory_proj_id,))
        fac_total_revenue = float(cur.fetchone()[0] or 0.0)

        cur.execute("""
            SELECT COALESCE(SUM(amount_usd), 0) 
            FROM transactions 
            WHERE project_id = %s AND direction = 'OUT' 
              AND tx_type NOT IN ('توزيع أرباح شريك', 'سداد زكاة') 
              AND settlement_id IS NULL;
        """, (factory_proj_id,))
        fac_total_expenses = float(cur.fetchone()[0] or 0.0)

        cur.execute("""
            SELECT COALESCE(SUM(t.amount_usd), 0)
            FROM transactions t
            JOIN stakeholders s ON t.stakeholder_id = s.id
            WHERE t.project_id = %s AND s.name LIKE %s 
              AND t.tx_type IN ('توزيع أرباح شريك', 'راتب او سلفة')
              AND t.settlement_id IS NULL;
        """, (factory_proj_id, '%أحمد شيخ%'))
        ahmed_withdrawals = float(cur.fetchone()[0] or 0.0)

        cur.execute("""
            SELECT COALESCE(SUM(t.amount_usd), 0)
            FROM transactions t
            JOIN stakeholders s ON t.stakeholder_id = s.id
            WHERE t.project_id = %s AND s.name LIKE %s 
              AND t.tx_type IN ('توزيع أرباح شريك', 'راتب او سلفة')
              AND t.settlement_id IS NULL;
        """, (factory_proj_id, '%مصعب%'))
        mosab_withdrawals = float(cur.fetchone()[0] or 0.0)

    gross_factory_profit = fac_total_revenue - fac_total_expenses
    zakat_deduction = (gross_factory_profit * 0.02) if gross_factory_profit > 0 else 0.0
    net_distributable = gross_factory_profit - zakat_deduction if gross_factory_profit > 0 else 0.0

    ahmed_share_75 = net_distributable * 0.75
    company_share_25 = net_distributable * 0.25
    ahmed_net_payable = ahmed_share_75 - ahmed_withdrawals
    company_net_payable = company_share_25 - mosab_withdrawals

    tab_dash, tab_settle, tab_history, tab_tx, tab_new = st.tabs([
        ":material/account_balance_wallet: أرصدة وسيولة المعمل", 
        ":material/balance: تصفية الأرباح الدورية",
        ":material/history: سجل التصفيات المؤرشفة", 
        ":material/receipt_long: سجل الحركات", 
        ":material/add_circle: إضافة حركة جديدة"
    ])

    with tab_dash:
        cf1, cf2 = st.columns(2)
        with cf1:
            st.markdown(f'<div class="metric-card"><div class="metric-title">صندوق المعمل (USD)</div><div class="metric-value-usd">{fac_bal_usd:,.2f} $</div></div>', unsafe_allow_html=True)
        with cf2:
            st.markdown(f'<div class="metric-card" style="border-top-color: #BE9D5F;"><div class="metric-title">صندوق المعمل (SYP)</div><div class="metric-value-gold">{fac_bal_syp:,.0f} ل.س</div></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("##### :material/query_stats: مؤشرات الدورة الحالية (غير المصفّاة)")
        cs1, cs2, cs3, cs4 = st.columns(4)
        with cs1: st.metric("المقبوضات غير المصفاة", f"{fac_total_revenue:,.2f} $")
        with cs2: st.metric("المصاريف غير المصفاة", f"{fac_total_expenses:,.2f} $")
        with cs3: st.metric("الربح الإجمالي الحالي", f"{gross_factory_profit:,.2f} $")
        with cs4: st.metric("مخصص الزكاة (2%)", f"{zakat_deduction:,.2f} $")

    with tab_settle:
        st.markdown("#### :material/table_view: جدول التصفية والأنصبة المستحقة")
        settle_data = [
            {"الطرف": "أحمد شيخ (المعمل)", "النسبة العقدية": "75%", "الأرباح المستحقة ($)": f"{ahmed_share_75:,.2f} $", "المسحوبات السابقة": f"{ahmed_withdrawals:,.2f} $", "الصافي المستحق للصرف": f"{ahmed_net_payable:,.2f} $"},
            {"الطرف": "مصعب المصري / شركة MA", "النسبة العقدية": "25%", "الأرباح المستحقة ($)": f"{company_share_25:,.2f} $", "المسحوبات السابقة": f"{mosab_withdrawals:,.2f} $", "الصافي المستحق للصرف": f"{company_net_payable:,.2f} $"},
            {"الطرف": "أمانة الزكاة (بيد أحمد شيخ)", "النسبة العقدية": "2% مقطوعة", "الأرباح المستحقة ($)": f"{zakat_deduction:,.2f} $", "المسحوبات السابقة": "0.00 $", "الصافي المستحق للصرف": f"{zakat_deduction:,.2f} $"}
        ]
        st.dataframe(pd.DataFrame(settle_data), use_container_width=True, hide_index=True)

        df_dates = run_query("""
            SELECT MIN(tx_date) AS s_date, MAX(tx_date) AS e_date, COUNT(id) AS cnt 
            FROM transactions 
            WHERE project_id = %s AND settlement_id IS NULL;
        """, (factory_proj_id,))
        
        has_tx = int(df_dates['cnt'].values[0]) > 0 if not df_dates.empty else False
        p_start = df_dates['s_date'].values[0] if has_tx and df_dates['s_date'].values[0] else datetime.now().date()
        p_end = df_dates['e_date'].values[0] if has_tx and df_dates['e_date'].values[0] else datetime.now().date()

        st.markdown("---")
        st.markdown("##### :material/lock: إغلاق وتثبيت دورة التصفية المحاسبية")
        
        if not has_tx:
            st.info("لا توجد حركات مالية غير مصفاة معلقة في الفترة الحالية.")
        else:
            st.caption(f"الفترة المعنية: من {p_start} إلى {p_end} (عدد الحركات المعلقة: {df_dates['cnt'].values[0]})")
            
            with st.form("execute_factory_settlement_form"):
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    settle_notes = st.text_input("ملاحظات دورة التصفية", value=f"تصفية دورية لمعمل الحجر حتى تاريخ {p_end}")
                    auto_payout = st.checkbox("ترحيل سندات صرف فورية للأرباح المتبقية", value=False)
                with col_s2:
                    current_user_name = st.session_state.user_info['full_name']
                    st.text_input("المسؤول المعتمد", value=current_user_name, disabled=True)

                if st.form_submit_button("اعتماد التصفية وإغلاق الفترة", icon=":material/check_circle:"):
                    settlement_key = f"SETTLE-FAC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    
                    try:
                        with get_db_cursor(commit=True) as (cur, _):
                            cur.execute("""
                                INSERT INTO factory_settlements (
                                    id, period_start, period_end, total_revenue_usd, total_expenses_usd, 
                                    gross_profit_usd, zakat_amount_usd, net_distributable_usd, 
                                    ahmed_share_usd, ahmed_withdrawals_usd, ahmed_net_payout_usd, 
                                    company_share_usd, company_withdrawals_usd, company_net_payout_usd, 
                                    settled_by, notes
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                            """, (
                                settlement_key, p_start, p_end, fac_total_revenue, fac_total_expenses,
                                gross_factory_profit, zakat_deduction, net_distributable,
                                ahmed_share_75, ahmed_withdrawals, ahmed_net_payable,
                                company_share_25, mosab_withdrawals, company_net_payable,
                                current_user_name, settle_notes
                            ))

                            cur.execute("""
                                UPDATE transactions 
                                SET settlement_id = %s 
                                WHERE project_id = %s AND settlement_id IS NULL;
                            """, (settlement_key, factory_proj_id))

                            if auto_payout:
                                cur.execute("SELECT id FROM stakeholders WHERE name LIKE '%أحمد شيخ%' LIMIT 1;")
                                r_ah = cur.fetchone()
                                s_ahmed_id = int(r_ah[0]) if r_ah else 1

                                cur.execute("SELECT id FROM stakeholders WHERE name LIKE '%مصعب%' LIMIT 1;")
                                r_mo = cur.fetchone()
                                s_mosab_id = int(r_mo[0]) if r_mo else 2

                                if ahmed_net_payable > 0:
                                    cur.execute("""
                                        INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description, settlement_id)
                                        VALUES (%s, CURRENT_DATE, 'توزيع أرباح شريك', %s, %s, %s, %s, 'USD', 1.0, %s, 'OUT', 'كاش من صندوق المعمل', %s, %s);
                                    """, (f"PAY-AHMED-{settlement_key}", factory_proj_id, s_ahmed_id, v_usd_id, ahmed_net_payable, ahmed_net_payable, f"صرف صافي أرباح تصفية {settlement_key}", settlement_key))

                                if company_net_payable > 0:
                                    cur.execute("""
                                        INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description, settlement_id)
                                        VALUES (%s, CURRENT_DATE, 'توزيع أرباح شريك', %s, %s, %s, %s, 'USD', 1.0, %s, 'OUT', 'كاش من صندوق المعمل', %s, %s);
                                    """, (f"PAY-MA-{settlement_key}", factory_proj_id, s_mosab_id, v_usd_id, company_net_payable, company_net_payable, f"صرف حصة الشركة من تصفية {settlement_key}", settlement_key))

                        st.success(f"تم إغلاق دورة التصفية وتوثيق القيد: {settlement_key}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"خطأ أثناء ترحيل التصفية: {e}")

    with tab_history:
        st.markdown("#### :material/history_edu: أرشيف دورات التصفية المعتمدة")
        df_history = run_query("""
            SELECT id AS "رقم التصفية", period_start AS "من تاريخ", period_end AS "إلى تاريخ",
                   total_revenue_usd AS "الإيرادات ($)", total_expenses_usd AS "المصاريف ($)",
                   gross_profit_usd AS "الربح الإجمالي ($)", zakat_amount_usd AS "الزكاة ($)",
                   ahmed_net_payout_usd AS "صافي المعمل (أحمد شيخ)", company_net_payout_usd AS "صافي الشركة (MA)",
                   settled_by AS "المعتمد", created_at AS "تاريخ التثبيت"
            FROM factory_settlements 
            ORDER BY created_at DESC;
        """)
        if not df_history.empty:
            st.dataframe(df_history.fillna("-"), use_container_width=True, hide_index=True)
            st.download_button("تصدير الأرشيف (Excel)", data=to_excel_download_link(df_history, "Factory_Settlements_Archive.xlsx"), file_name="Factory_Settlements_Archive.xlsx", icon=":material/table_view:")
        else:
            st.info("لا توجد دورات تصفية مؤرشفة.")

    with tab_tx:
        st.markdown("#### :material/list_alt: سجل الحركات المفصل للمعمل")
        df_fac_txs = run_query("""
            SELECT t.id AS "رقم الفاتورة", t.tx_date AS "التاريخ", t.tx_type AS "نوع الحركة",
                   COALESCE(s.name, 'عام') AS "الطرف المرتبط", t.amount AS "المبلغ",
                   CASE WHEN t.currency = 'USD' THEN 'دولار ($)' ELSE 'ليرة سورية' END AS "العملة",
                   t.amount_usd AS "المعادل بالدولار ($)",
                   CASE WHEN t.direction = 'IN' THEN 'وارد (قبض)' ELSE 'صادر (صرف)' END AS "الاتجاه",
                   CASE WHEN t.settlement_id IS NOT NULL THEN 'مصفاة' ELSE 'جارية' END AS "حالة التصفية",
                   t.settlement_id AS "رقم قيد التصفية",
                   t.payment_method AS "طريقة الدفع", t.description AS "البيان"
            FROM transactions t
            LEFT JOIN stakeholders s ON t.stakeholder_id = s.id
            WHERE t.project_id = %s
            ORDER BY t.tx_date DESC, t.id DESC;
        """, (factory_proj_id,))
        if not df_fac_txs.empty:
            st.dataframe(df_fac_txs.fillna("-"), use_container_width=True, hide_index=True)
            st.download_button("تصدير الحركات (Excel)", data=to_excel_download_link(df_fac_txs, "Factory_Stone.xlsx"), file_name="Factory_Stone.xlsx", icon=":material/table_view:")
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

            if st.form_submit_button("حفظ وترحيل القيد", icon=":material/save:"):
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
