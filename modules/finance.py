import streamlit as st
import pandas as pd
from datetime import datetime
from core.db import run_query, get_db_cursor
from core.utils import to_excel_download_link, get_next_invoice_id
from core.pdf_engine import generate_receipt_pdf

def render_vault_transfers(current_user):
    st.subheader("💱 المصارفة والتحويل المالي بين الصناديق")
    df_v = run_query("SELECT id, currency, COALESCE(SUM(CASE WHEN t.direction = 'IN' THEN t.amount ELSE -t.amount END), 0) AS balance FROM vaults v LEFT JOIN transactions t ON v.id = t.vault_id WHERE v.name NOT LIKE '%معمل الحجر%' GROUP BY v.id, v.currency;")
    usd_avail = float(df_v.loc[df_v['currency'] == 'USD', 'balance'].values[0]) if not df_v.empty else 0.0
    syp_avail = float(df_v.loc[df_v['currency'] == 'SYP', 'balance'].values[0]) if not df_v.empty else 0.0

    st.info(f"💵 الرصيد المتاح: **{usd_avail:,.2f} $** | 🪙 الرصيد بالليرة: **{syp_avail:,.0f} ل.س**")
    if current_user['role'] in ["Admin", "Accountant"]:
        with st.form("transfer_vault_form"):
            ct1, ct2, ct3 = st.columns(3)
            with ct1:
                tx_dir = st.selectbox("الاتجاه", ["من دولار إلى ليرة سورية (صرافة لليرة)", "من ليرة سورية إلى دولار (شراء دولار)"])
                t_date = st.date_input("التاريخ", datetime.now().date())
            with ct2:
                s_amt = st.number_input("المبلغ المراد تحويله", min_value=0.0, step=50.0)
                rate = st.number_input("سعر الصرف", min_value=1.0, value=131.0)
            with ct3:
                calc_res = s_amt * rate if "من دولار" in tx_dir else (s_amt / rate if rate > 0 else 0)
                st.markdown(f"**المقابل المستلم:** {calc_res:,.2f}")
                notes = st.text_input("البيان / مكتب الصرافة", value="صرافة داخلية بين الصناديق")

            if st.form_submit_button("🚀 اعتماد الصرافة وترحيل القيدين"):
                from_c = "USD" if "من دولار" in tx_dir else "SYP"
                to_c = "SYP" if "من دولار" in tx_dir else "USD"
                avail = usd_avail if from_c == "USD" else syp_avail
                if 0 < s_amt <= avail:
                    ts = int(datetime.now().timestamp())
                    v_src = 1 if from_c == "USD" else 2
                    v_dst = 2 if to_c == "SYP" else 1
                    amt_usd = s_amt if from_c == "USD" else calc_res
                    with get_db_cursor(commit=True) as (cur, _):
                        cur.execute("INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description) VALUES (%s, %s, 'تحويل بين الصناديق (صادر)', 2, 1, %s, %s, %s, %s, %s, 'OUT', 'صرافة', %s);", (f"TRF-O-{ts}", t_date, v_src, s_amt, from_c, rate, amt_usd, notes))
                        cur.execute("INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description) VALUES (%s, %s, 'تحويل بين الصناديق (وارد)', 2, 1, %s, %s, %s, %s, %s, 'IN', 'صرافة', %s);", (f"TRF-I-{ts}", t_date, v_dst, calc_res, to_c, rate, amt_usd, notes))
                    st.success("تم ترحيل قيدي الصرافة بنجاح.")
                    st.rerun()
                else:
                    st.error("الرصيد المتاح غير كافٍ لإتمام العملية.")

def render_vouchers_and_reports():
    st.subheader("🖨️ توليد السندات الرسمية وتصدير البيانات")
    tab_pdf, tab_ex = st.tabs(["📄 توليد سند رسمي (PDF)", "📊 تصدير الحركات إلى Excel"])

    with tab_pdf:
        tx_options = run_query("""
            SELECT t.id, t.amount, t.currency, s.name AS s_name 
            FROM transactions t 
            LEFT JOIN stakeholders s ON t.stakeholder_id = s.id 
            ORDER BY t.tx_date DESC LIMIT 50;
        """)
        if not tx_options.empty:
            tx_labels = [f"{r['id']} | {r['amount']} {r['currency']} | {r['s_name']}" for _, r in tx_options.iterrows()]
            chosen_label = st.selectbox("اختر السند:", tx_labels)
            chosen_id = chosen_label.split(" | ")[0]

            with get_db_cursor() as (cur, _):
                cur.execute("SELECT t.id, t.tx_date, t.tx_type, COALESCE(p.name, 'عام'), COALESCE(s.name, 'عام'), t.amount, t.currency, t.exchange_rate, t.amount_usd, t.payment_method, t.description FROM transactions t LEFT JOIN projects p ON t.project_id = p.id LEFT JOIN stakeholders s ON t.stakeholder_id = s.id WHERE t.id = %s;", (chosen_id,))
                tx_r = cur.fetchone()
                tx_dict = {'id': tx_r[0], 'tx_date': tx_r[1], 'tx_type': tx_r[2], 'project_name': tx_r[3], 'stakeholder_name': tx_r[4], 'amount': float(tx_r[5]), 'currency': tx_r[6], 'exchange_rate': float(tx_r[7]), 'amount_usd': float(tx_r[8]), 'payment_method': tx_r[9], 'description': tx_r[10] or ''}
                cur.execute("SELECT item_name, category, quantity, unit_price, total_price FROM invoice_items WHERE transaction_id = %s;", (chosen_id,))
                items_r = cur.fetchall()

            pdf_bytes = generate_receipt_pdf(tx_dict, items_r)
            st.download_button("📥 تحميل ملف السند (PDF)", data=pdf_bytes, file_name=f"Voucher_{chosen_id}.pdf", mime="application/pdf")

    with tab_ex:
        df_all_tx = run_query("""
            SELECT t.id AS "رقم الفاتورة", t.tx_date AS "التاريخ", t.tx_type AS "نوع الحركة", 
                   p.name AS "المشروع", s.name AS "الطرف", t.amount AS "المبلغ", t.currency AS "العملة", 
                   t.amount_usd AS "المعادل بالدولار ($)", t.direction AS "الاتجاه", t.payment_method AS "طريقة الدفع", t.description AS "البيان"
            FROM transactions t 
            LEFT JOIN projects p ON t.project_id = p.id 
            LEFT JOIN stakeholders s ON t.stakeholder_id = s.id 
            ORDER BY t.tx_date DESC;
        """)
        st.download_button("📥 تصدير السجل المحاسبي الكامل (Excel)", data=to_excel_download_link(df_all_tx, "Transactions_Report.xlsx"), file_name="MA_Transactions.xlsx")

def render_transactions_ledger():
    st.subheader("📑 دفتر الحركات وسجل الفواتير التفصيلي")
    df_unified = run_query("""
        SELECT t.id AS "رقم الفاتورة", COALESCE(ii.id::text, '-') AS "رقم البند",
               t.tx_date AS "التاريخ", t.tx_type AS "نوع الحركة", p.name AS "المشروع",
               COALESCE(s_item.name, s_tx.name, 'غير محدد') AS "المستفيد / المورد",
               COALESCE(ii.item_name, t.description, '-') AS "البند / البيان",
               COALESCE(ii.category, '-') AS "التصنيف",
               COALESCE(ii.quantity::text, '-') AS "الكمية",
               COALESCE(ii.unit_price::text, '-') AS "السعر الإفرادي",
               COALESCE(ii.total_price, t.amount) AS "المبلغ",
               COALESCE(ii.currency, t.currency) AS "العملة",
               t.amount_usd AS "إجمالي الفاتورة ($)",
               t.payment_method AS "طريقة الدفع"
        FROM transactions t
        LEFT JOIN projects p ON t.project_id = p.id
        LEFT JOIN stakeholders s_tx ON t.stakeholder_id = s_tx.id
        LEFT JOIN invoice_items ii ON t.id = ii.transaction_id
        LEFT JOIN stakeholders s_item ON ii.stakeholder_id = s_item.id
        WHERE p.project_type != 'Factory' OR p.project_type IS NULL
        ORDER BY t.tx_date DESC, t.id DESC, ii.id ASC;
    """)
    st.dataframe(df_unified.fillna("-"), use_container_width=True, hide_index=True)
    st.download_button("📥 تصدير السجل المالي التفصيلي (Excel)", data=to_excel_download_link(df_unified, "Detailed_Ledger.xlsx"), file_name="Detailed_Ledger.xlsx")

def render_add_invoice(current_user):
    if current_user['role'] in ["Admin", "Accountant"]:
        st.subheader("📄 تسجيل فاتورة / حركة مالية")
        projs = run_query("SELECT id, name FROM projects WHERE project_type != 'Factory' ORDER BY name;")
        parties = run_query("SELECT id, name FROM stakeholders ORDER BY name;")
        auto_inv = get_next_invoice_id()

        mode = st.radio("نوع الإدخال:", ["سند مالي مباشر (بدون بنود تفصيلية)", "فاتورة تفصيلية متعددة البنود"])

        if "بدون بنود" in mode:
            with st.form("simple_tx_form", clear_on_submit=True):
                ca1, ca2, ca3 = st.columns(3)
                with ca1:
                    inv_id = st.text_input("رقم السند", value=auto_inv)
                    t_date = st.date_input("التاريخ", datetime.now().date())
                    t_type = st.selectbox("نوع الحركة", ["دفعة لمشروع", "مقبوضات من مستثمر", "مصروف عام", "راتب او سلفة", "توزيع أرباح شريك", "ايراد عام"])
                with ca2:
                    p_name = st.selectbox("المشروع", projs['name'].tolist())
                    part_name = st.selectbox("الطرف", parties['name'].tolist())
                    method = st.selectbox("طريقة الدفع", ["كاش (نقداً)", "حوالة مصرفية", "شيك بنكي"])
                with ca3:
                    curr_choice = st.selectbox("العملة", ["USD", "SYP"])
                    rate_val = st.number_input("سعر الصرف", min_value=1.0, value=1.0 if curr_choice == "USD" else 131.0)
                    amount_val = st.number_input("المبلغ الإجمالي", min_value=0.0, step=50.0)

                desc_val = st.text_area("البيان والملاحظات")
                if st.form_submit_button("💾 حفظ وترحيل السند"):
                    if amount_val > 0:
                        p_id = int(projs.loc[projs['name'] == p_name, 'id'].values[0])
                        s_id = int(parties.loc[parties['name'] == part_name, 'id'].values[0])
                        v_id = 1 if curr_choice == 'USD' else 2
                        dir_m = 'IN' if any(k in t_type for k in ['مقبوضات', 'ايراد']) else 'OUT'
                        amt_u = float(amount_val if curr_choice == 'USD' else (amount_val / rate_val))
                        with get_db_cursor(commit=True) as (cur, _):
                            cur.execute("""
                                INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                            """, (str(inv_id), t_date, str(t_type), p_id, s_id, v_id, float(amount_val), curr_choice, float(rate_val), float(amt_u), dir_m, method, desc_val))
                        st.success(f"تم حفظ السند {inv_id} بنجاح.")
                        st.rerun()
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                inv_id_m = st.text_input("رقم الفاتورة", value=auto_inv)
                t_date_m = st.date_input("التاريخ", datetime.now().date())
            with c2:
                p_name_m = st.selectbox("المشروع", projs['name'].tolist())
                t_type_m = st.selectbox("نوع الحركة", ["دفعة لمشروع", "شراء مواد وتخزين", "مصروف عام", "ايراد عام"])
            with c3:
                curr_m = st.selectbox("العملة", ["USD", "SYP"])
                rate_m = st.number_input("سعر الصرف", min_value=1.0, value=1.0 if curr_m == "USD" else 131.0)
                method_m = st.selectbox("طريقة الدفع", ["كاش (نقداً)", "حوالة مصرفية", "شيك بنكي"])

            desc_m = st.text_input("البيان العام", value="فاتورة مواد وتنفيذ متعددة البنود")
            cats = ["مواد بناء وتأسيس", "إكساء وتشطيب", "أجور معلمين", "أدوات ومعدات", "نقل وشحن", "أخرى"]
            p_list = parties['name'].tolist()

            default_df = pd.DataFrame([{"اسم البند": "", "التصنيف": cats[0], "الكمية": 1.0, "السعر الإفرادي": 0.0, "الطرف المستفيد": p_list[0]}])
            edited_df = st.data_editor(default_df, num_rows="dynamic", use_container_width=True)

            valid_items = edited_df[edited_df["اسم البند"].str.strip() != ""].copy()
            if not valid_items.empty:
                valid_items["المجموع"] = valid_items["الكمية"].astype(float) * valid_items["السعر الإفرادي"].astype(float)
                total_computed = float(valid_items["المجموع"].sum())
                st.markdown(f"### 💰 الإجمالي: **{total_computed:,.2f} {curr_m}**")

                if st.button("🚀 حفظ الفاتورة وبنودها كاملة"):
                    if total_computed > 0:
                        p_id = int(projs.loc[projs['name'] == p_name_m, 'id'].values[0])
                        v_id = 1 if curr_m == 'USD' else 2
                        dir_m = 'IN' if any(k in t_type_m for k in ['مقبوضات', 'ايراد']) else 'OUT'
                        amt_u = float(total_computed if curr_m == 'USD' else (total_computed / rate_m))
                        first_party = valid_items.iloc[0]["الطرف المستفيد"]
                        primary_s_id = int(parties.loc[parties['name'] == first_party, 'id'].values[0])

                        with get_db_cursor(commit=True) as (cur, _):
                            cur.execute("""
                                INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                            """, (str(inv_id_m), t_date_m, str(t_type_m), p_id, primary_s_id, v_id, total_computed, curr_m, rate_m, amt_u, dir_m, method_m, desc_m))
                            
                            for _, r in valid_items.iterrows():
                                item_s_id = int(parties.loc[parties['name'] == r["الطرف المستفيد"], 'id'].values[0])
                                cur.execute("""
                                    INSERT INTO invoice_items (transaction_id, item_name, category, quantity, unit_price, total_price, stakeholder_id, currency)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                                """, (str(inv_id_m), str(r["اسم البند"]).strip(), str(r["التصنيف"]), float(r["الكمية"]), float(r["السعر الإفرادي"]), float(r["المجموع"]), item_s_id, curr_m))
                        st.success("تم حفظ الفاتورة وبنودها بنجاح.")
                        st.rerun()

def render_edit_transactions(current_user):
    if current_user['role'] in ["Admin", "Accountant"]:
        st.subheader("✏️ استعراض وتعديل أو حذف الفواتير")
        all_tx = run_query("SELECT id, tx_date, amount, currency, description FROM transactions ORDER BY tx_date DESC LIMIT 50;")
        if not all_tx.empty:
            sel_str = st.selectbox("اختر الفاتورة:", [f"{r['id']} | {r['tx_date']} | {r['amount']} {r['currency']} | {r['description']}" for _, r in all_tx.iterrows()])
            sel_id = sel_str.split(" | ")[0]
            if st.button(f"🗑️ حذف الفاتورة {sel_id} نهائياً"):
                with get_db_cursor(commit=True) as (cur, _):
                    cur.execute("DELETE FROM invoice_items WHERE transaction_id = %s;", (sel_id,))
                    cur.execute("DELETE FROM transactions WHERE id = %s;", (sel_id,))
                st.success(f"تم حذف الفاتورة {sel_id}.")
                st.rerun()

def render_investor_statements():
    st.subheader("📑 كشوفات حسابات المستثمرين والعملاء")
    all_projs = run_query("SELECT id, name, management_fee_rate FROM projects WHERE project_type NOT IN ('Internal', 'Factory') ORDER BY name;")
    if not all_projs.empty:
        selected_proj = st.selectbox("المشروع", all_projs['name'].tolist())
        p_row = all_projs[all_projs['name'] == selected_proj].iloc[0]
        p_id = int(p_row['id'])
        f_rate = float(p_row['management_fee_rate'])

        with get_db_cursor() as (cur, _):
            cur.execute("SELECT COALESCE(SUM(amount_usd), 0) FROM transactions WHERE project_id = %s AND direction = 'IN';", (p_id,))
            paid_in = float(cur.fetchone()[0] or 0.0)
            cur.execute("SELECT COALESCE(SUM(amount_usd), 0) FROM transactions WHERE project_id = %s AND direction = 'OUT';", (p_id,))
            costs_out = float(cur.fetchone()[0] or 0.0)

        mgmt_fee = costs_out * f_rate
        net_balance = (costs_out + mgmt_fee) - paid_in

        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("المقبوض من المستثمر", f"{paid_in:,.2f} $")
        with c2: st.metric("تكاليف ومواد التنفيذ", f"{costs_out:,.2f} $")
        with c3: st.metric(f"أتعاب الإدارة ({f_rate*100:.0f}%)", f"{mgmt_fee:,.2f} $")
        with c4: st.metric("الصافي المستحق", f"{net_balance:,.2f} $")

        df_inv_tx = run_query("""
            SELECT id AS "رقم الفاتورة", tx_date AS "التاريخ", tx_type AS "نوع الحركة",
                   amount AS "المبلغ", currency AS "العملة", amount_usd AS "المعادل بالدولار ($)", description AS "البيان"
            FROM transactions WHERE project_id = %s ORDER BY tx_date DESC;
        """, (p_id,))
        st.dataframe(df_inv_tx.fillna("-"), use_container_width=True, hide_index=True)
    else:
        st.info("لا توجد مشاريع استثمارية مسجلة.")

def render_projects_overview():
    st.subheader("🏢 كشف أتعاب الإدارة وتكاليف المشاريع")
    st.dataframe(run_query("""
        SELECT p.name AS "المشروع",
               CASE WHEN p.status = 'Active' THEN 'نشط 🟢' ELSE 'مكتمل 🏁' END AS "الحالة",
               p.management_fee_rate * 100 AS "أتعاب الإدارة %",
               COALESCE(SUM(CASE WHEN t.direction = 'OUT' THEN t.amount_usd ELSE 0 END), 0) AS "المصاريف ($)",
               ROUND(COALESCE(SUM(CASE WHEN t.direction = 'OUT' THEN t.amount_usd ELSE 0 END), 0) * p.management_fee_rate, 2) AS "أتعاب الإدارة المستحقة ($)",
               COALESCE(SUM(CASE WHEN t.direction = 'IN' THEN t.amount_usd ELSE 0 END), 0) AS "المقبوض من المستثمر ($)"
        FROM projects p 
        LEFT JOIN transactions t ON p.id = t.project_id 
        WHERE p.project_type NOT IN ('Internal', 'Factory') 
        GROUP BY p.id, p.name, p.status, p.management_fee_rate;
    """).fillna("-"), use_container_width=True, hide_index=True)
