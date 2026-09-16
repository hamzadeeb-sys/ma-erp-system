import streamlit as st
import pandas as pd
from datetime import datetime, date
from core.db import run_query, get_db_cursor
from core.utils import to_excel_download_link, get_next_invoice_id
from core.pdf_engine import generate_receipt_pdf

def render_pnl_statement():
    st.subheader(":material/monitoring: تقرير الأرباح والخسائر الشامل (P&L Income Statement)")
    st.caption("التحليل المالي الموحد لإيرادات ومصاريف الشركة التشغيلية والإدارية")

    # 1. نطاق التاريخ المالي
    col_d1, col_d2, col_d3 = st.columns([1.5, 1.5, 2])
    with col_d1:
        start_date = st.date_input("من تاريخ", date(date.today().year, 1, 1))
    with col_d2:
        end_date = st.date_input("إلى تاريخ", date.today())
    with col_d3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        st.caption(f"الفترة المعتمدة: من {start_date} إلى {end_date}")

    # 2. احتساب الإيرادات والمصاريف
    with get_db_cursor() as (cur, _):
        # التحقق من معرف مشروع المعمل لتفادي التثبيت العشوائي
        cur.execute("SELECT id FROM projects WHERE name = 'معمل الحجر الصناعي' LIMIT 1;")
        fac_proj_res = cur.fetchone()
        factory_proj_id = int(fac_proj_res[0]) if fac_proj_res else 1

        # أ. أتعاب إدارة المشاريع المستحقة
        cur.execute("""
            SELECT COALESCE(SUM(ROUND(t.amount_usd * p.management_fee_rate, 2)), 0)
            FROM projects p 
            JOIN transactions t ON p.id = t.project_id
            WHERE t.direction = 'OUT' 
              AND p.project_type NOT IN ('Internal', 'Factory')
              AND t.tx_date BETWEEN %s AND %s;
        """, (start_date, end_date))
        mgmt_fees_revenue = float(cur.fetchone()[0] or 0.0)

        # ب. حصة الشركة من معمل الحجر (المعتمدة + الجارية)
        cur.execute("""
            SELECT COALESCE(SUM(company_net_payout_usd), 0)
            FROM factory_settlements
            WHERE period_end BETWEEN %s AND %s;
        """, (start_date, end_date))
        factory_settled_share = float(cur.fetchone()[0] or 0.0)

        cur.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN direction = 'IN' THEN amount_usd ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN direction = 'OUT' AND tx_type NOT IN ('توزيع أرباح شريك', 'سداد زكاة') THEN amount_usd ELSE 0 END), 0)
            FROM transactions
            WHERE project_id = %s AND settlement_id IS NULL AND tx_date BETWEEN %s AND %s;
        """, (factory_proj_id, start_date, end_date))
        raw_fac_profit = float(cur.fetchone()[0] or 0.0)
        factory_unsettled_share = (raw_fac_profit * 0.98 * 0.25) if raw_fac_profit > 0 else 0.0

        total_factory_revenue = factory_settled_share + factory_unsettled_share

        # ج. أرباح وخسائر الصرافة
        cur.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN fx_gain_loss > 0 THEN fx_gain_loss ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN fx_gain_loss < 0 THEN ABS(fx_gain_loss) ELSE 0 END), 0)
            FROM transactions
            WHERE tx_date BETWEEN %s AND %s;
        """, (start_date, end_date))
        fx_row = cur.fetchone()
        fx_gains_syp = float(fx_row[0] or 0.0)
        fx_losses_syp = float(fx_row[1] or 0.0)

        cur.execute("SELECT exchange_rate FROM transactions WHERE currency = 'SYP' ORDER BY tx_date DESC LIMIT 1;")
        rate_rec = cur.fetchone()
        active_rate = float(rate_rec[0]) if (rate_rec and rate_rec[0]) else 131.0
        fx_gains_usd = fx_gains_syp / active_rate if active_rate > 0 else 0.0
        fx_losses_usd = fx_losses_syp / active_rate if active_rate > 0 else 0.0

        # د. إيرادات عامة (مع تمرير نمط البحث كـ parameter آمن لحل IndexError)
        cur.execute("""
            SELECT COALESCE(SUM(amount_usd), 0)
            FROM transactions
            WHERE tx_type = 'ايراد عام' 
              AND (description IS NULL OR description NOT LIKE %s)
              AND tx_date BETWEEN %s AND %s;
        """, ('%راس مال%', start_date, end_date))
        other_incomes_usd = float(cur.fetchone()[0] or 0.0)

        # هـ. مصاريف الرواتب والأجور
        cur.execute("""
            SELECT COALESCE(SUM(amount_usd), 0)
            FROM transactions
            WHERE tx_type = 'راتب او سلفة' 
              AND (project_id != %s OR project_id IS NULL)
              AND tx_date BETWEEN %s AND %s;
        """, (factory_proj_id, start_date, end_date))
        payroll_expenses_usd = float(cur.fetchone()[0] or 0.0)

        # و. المصاريف العامة والتشغيلية
        cur.execute("""
            SELECT COALESCE(SUM(amount_usd), 0)
            FROM transactions
            WHERE tx_type = 'مصروف عام' 
              AND (project_id != %s OR project_id IS NULL)
              AND tx_date BETWEEN %s AND %s;
        """, (factory_proj_id, start_date, end_date))
        general_expenses_usd = float(cur.fetchone()[0] or 0.0)

    # 3. الحسابات الصافية
    total_revenues_usd = mgmt_fees_revenue + total_factory_revenue + fx_gains_usd + other_incomes_usd
    total_expenses_usd = payroll_expenses_usd + general_expenses_usd + fx_losses_usd
    net_profit_usd = total_revenues_usd - total_expenses_usd
    profit_margin = (net_profit_usd / total_revenues_usd * 100) if total_revenues_usd > 0 else 0.0

    # 4. المؤشرات العلوية
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f'<div class="metric-card"><div class="metric-title">إجمالي الإيرادات ($)</div><div class="metric-value-usd">{total_revenues_usd:,.2f} $</div></div>', unsafe_allow_html=True)
    with k2:
        st.markdown(f'<div class="metric-card" style="border-top-color: #A29F98;"><div class="metric-title">إجمالي المصاريف ($)</div><div class="metric-value-gold" style="color: #BA1A1A;">{total_expenses_usd:,.2f} $</div></div>', unsafe_allow_html=True)
    with k3:
        color_np = "#0F4733" if net_profit_usd >= 0 else "#BA1A1A"
        st.markdown(f'<div class="metric-card" style="border-top-color: {color_np};"><div class="metric-title">صافي الربح الفعلي ($)</div><div class="metric-value-usd" style="color: {color_np};">{net_profit_usd:,.2f} $</div></div>', unsafe_allow_html=True)
    with k4:
        st.markdown(f'<div class="metric-card" style="border-top-color: #BE9D5F;"><div class="metric-title">هامش الربحية الصافي</div><div class="metric-value-gold">{profit_margin:.1f}%</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # 5. جدول القائمة المحاسبية
    pnl_structure = [
        {"البند المحاسبي": "أولاً: الإيرادات التشغيلية والاستثمارية (Operating Revenues)", "التصنيف": "عنوان رئيسي", "القيمة ($)": ""},
        {"البند المحاسبي": "  - أتعاب إدارة وتنفيذ المشاريع العقارية", "التصنيف": "إيراد", "القيمة ($)": f"{mgmt_fees_revenue:,.2f}"},
        {"البند المحاسبي": "  - حصة الشركة من أرباح معمل الحجر الصناعي (25%)", "التصنيف": "إيراد", "القيمة ($)": f"{total_factory_revenue:,.2f}"},
        {"البند المحاسبي": "  - أرباح فروقات أسعار الصرف المحققة (FX Gains)", "التصنيف": "إيراد", "القيمة ($)": f"{fx_gains_usd:,.2f}"},
        {"البند المحاسبي": "  - إيرادات استشارية وعامة أخرى", "التصنيف": "إيراد", "القيمة ($)": f"{other_incomes_usd:,.2f}"},
        {"البند المحاسبي": "مجموع الإيرادات الإجمالية", "التصنيف": "إجمالي وسيط", "القيمة ($)": f"{total_revenues_usd:,.2f}"},
        {"البند المحاسبي": "ثانياً: المصاريف التشغيلية والإدارية (Operating Expenses)", "التصنيف": "عنوان رئيسي", "القيمة ($)": ""},
        {"البند المحاسبي": "  - مسيرات الرواتب والأجور الشهرية والمكافآت", "التصنيف": "مصروف", "القيمة ($)": f"{payroll_expenses_usd:,.2f}"},
        {"البند المحاسبي": "  - مصاريف عمومية وإدارية ونثريات وتجهيز المقر", "التصنيف": "مصروف", "القيمة ($)": f"{general_expenses_usd:,.2f}"},
        {"البند المحاسبي": "  - خسائر فروقات أسعار الصرف المحققة (FX Losses)", "التصنيف": "مصروف", "القيمة ($)": f"{fx_losses_usd:,.2f}"},
        {"البند المحاسبي": "مجموع المصاريف التشغيلية", "التصنيف": "إجمالي وسيط", "القيمة ($)": f"{total_expenses_usd:,.2f}"},
        {"البند المحاسبي": "صافي الربح / الخسارة الصافي للشركة (Net Income)", "التصنيف": "النتيجة النهائية", "القيمة ($)": f"{net_profit_usd:,.2f}"}
    ]

    df_pnl = pd.DataFrame(pnl_structure)
    st.dataframe(df_pnl, use_container_width=True, hide_index=True)

    st.download_button(
        "تصدير قائمة الأرباح والخسائر الرسمية (Excel)", 
        data=to_excel_download_link(df_pnl, "Income_Statement_PL.xlsx"), 
        file_name=f"MA_PL_Statement_{start_date}_{end_date}.xlsx", 
        icon=":material/table_view:"
    )

def render_vault_transfers(current_user):
    st.subheader(":material/currency_exchange: المصارفة والتحويل المالي بين الصناديق")
    df_v = run_query("""
        SELECT id, currency, COALESCE(SUM(CASE WHEN t.direction = 'IN' THEN t.amount ELSE -t.amount END), 0) AS balance 
        FROM vaults v 
        LEFT JOIN transactions t ON v.id = t.vault_id 
        WHERE v.name NOT LIKE '%معمل الحجر%' 
        GROUP BY v.id, v.currency;
    """)
    usd_avail = float(df_v.loc[df_v['currency'] == 'USD', 'balance'].values[0]) if not df_v.empty and 'USD' in df_v['currency'].values else 0.0
    syp_avail = float(df_v.loc[df_v['currency'] == 'SYP', 'balance'].values[0]) if not df_v.empty and 'SYP' in df_v['currency'].values else 0.0

    st.info(f"الرصيد المتاح بالدولار: {usd_avail:,.2f} $ | الرصيد المتاح بالليرة: {syp_avail:,.0f} ل.س")
    
    if current_user['role'] in ["Admin", "Accountant"]:
        with st.form("transfer_vault_form", clear_on_submit=True):
            ct1, ct2, ct3 = st.columns(3)
            with ct1:
                tx_dir = st.selectbox(
                    "اتجاه العملية", 
                    ["من دولار إلى ليرة سورية (بيع دولار)", "من ليرة سورية إلى دولار (شراء دولار)"],
                    index=None,
                    placeholder="اختر اتجاه الصرافة..."
                )
                t_date = st.date_input("التاريخ", datetime.now().date())
            with ct2:
                s_amt = st.number_input("المبلغ المحوّل", min_value=0.0, value=None, placeholder="0.00", step=50.0)
                actual_rate = st.number_input("سعر الصرف الفعلي للعملية", min_value=1.0, value=None, placeholder="أدخل السعر الفعلي...", step=0.5)
            with ct3:
                benchmark_rate = st.number_input("سعر الصرف الدفتري المرجعي", min_value=1.0, value=None, placeholder="أدخل السعر المعياري...", step=0.5)
                notes = st.text_input("البيان / مكتب الصرافة", placeholder="أدخل تفاصيل ومكتب الصرافة...")

            amt_val = float(s_amt or 0.0)
            act_r = float(actual_rate or 0.0)
            bench_r = float(benchmark_rate or 0.0)

            if tx_dir and amt_val > 0 and act_r > 0:
                calc_res = amt_val * act_r if "من دولار" in tx_dir else (amt_val / act_r if act_r > 0 else 0)
                st.markdown(f"**المقابل الدفتري المحتسب:** {calc_res:,.2f}")
            else:
                calc_res = 0.0

            if st.form_submit_button("اعتماد الصرافة وترحيل القيود", icon=":material/sync_alt:"):
                if not tx_dir or amt_val <= 0 or act_r <= 0 or bench_r <= 0:
                    st.error("يرجى ملء كافة حقول الصرافة وتحديد أسعار الصرف بدقة.")
                else:
                    from_c = "USD" if "من دولار" in tx_dir else "SYP"
                    to_c = "SYP" if "من دولار" in tx_dir else "USD"
                    avail = usd_avail if from_c == "USD" else syp_avail
                    
                    if 0 < amt_val <= avail:
                        ts = int(datetime.now().timestamp())
                        v_src = 1 if from_c == "USD" else 2
                        v_dst = 2 if to_c == "SYP" else 1
                        amt_usd = amt_val if from_c == "USD" else calc_res
                        
                        if from_c == "USD":
                            fx_diff = (act_r - bench_r) * amt_val
                        else:
                            fx_diff = (bench_r - act_r) * calc_res

                        with get_db_cursor(commit=True) as (cur, _):
                            cur.execute("""
                                INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description, fx_gain_loss)
                                VALUES (%s, %s, 'تحويل بين الصناديق (صادر)', 2, 1, %s, %s, %s, %s, %s, 'OUT', 'صرافة', %s, %s);
                            """, (f"TRF-O-{ts}", t_date, v_src, amt_val, from_c, act_r, amt_usd, notes or "صرافة داخلية", 0.0))
                            
                            cur.execute("""
                                INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description, fx_gain_loss)
                                VALUES (%s, %s, 'تحويل بين الصناديق (وارد)', 2, 1, %s, %s, %s, %s, %s, 'IN', 'صرافة', %s, %s);
                            """, (f"TRF-I-{ts}", t_date, v_dst, calc_res, to_c, act_r, amt_usd, notes or "صرافة داخلية", fx_diff))
                        
                        if fx_diff > 0:
                            st.success(f"تم ترحيل القيدين بنجاح. أرباح فروقات صرف: {fx_diff:,.2f} SYP")
                        elif fx_diff < 0:
                            st.warning(f"تم ترحيل القيدين بنجاح. خسائر فروقات صرف: {abs(fx_diff):,.2f} SYP")
                        else:
                            st.success("تم ترحيل قيدي الصرافة بنجاح.")
                        st.rerun()
                    else:
                        st.error("الرصيد المتاح في الصندوق المصدر غير كافٍ.")

def render_vouchers_and_reports():
    st.subheader(":material/print: التقارير وتوليد السندات الرسمية")
    tab_pdf, tab_ex = st.tabs([":material/picture_as_pdf: سند مالي رسمي", ":material/table_view: تصدير إلى Excel"])

    with tab_pdf:
        tx_options = run_query("""
            SELECT t.id, t.amount, t.currency, s.name AS s_name 
            FROM transactions t 
            LEFT JOIN stakeholders s ON t.stakeholder_id = s.id 
            ORDER BY t.tx_date DESC, t.id DESC LIMIT 50;
        """)
        if not tx_options.empty:
            tx_labels = [f"{r['id']} | {r['amount']} {r['currency']} | {r['s_name']}" for _, r in tx_options.iterrows()]
            chosen_label = st.selectbox("اختر السند المالي المطلوب:", tx_labels, index=None, placeholder="اختر السند...")
            
            if chosen_label:
                chosen_id = chosen_label.split(" | ")[0]
                with get_db_cursor() as (cur, _):
                    cur.execute("""
                        SELECT t.id, t.tx_date, t.tx_type, COALESCE(p.name, 'عام'), COALESCE(s.name, 'عام'), 
                               t.amount, t.currency, t.exchange_rate, t.amount_usd, t.payment_method, t.description 
                        FROM transactions t 
                        LEFT JOIN projects p ON t.project_id = p.id 
                        LEFT JOIN stakeholders s ON t.stakeholder_id = s.id 
                        WHERE t.id = %s;
                    """, (chosen_id,))
                    tx_r = cur.fetchone()
                    tx_dict = {
                        'id': tx_r[0], 'tx_date': tx_r[1], 'tx_type': tx_r[2], 
                        'project_name': tx_r[3], 'stakeholder_name': tx_r[4], 
                        'amount': float(tx_r[5]), 'currency': tx_r[6], 
                        'exchange_rate': float(tx_r[7]), 'amount_usd': float(tx_r[8]), 
                        'payment_method': tx_r[9], 'description': tx_r[10] or ''
                    }
                    cur.execute("""
                        SELECT item_name, category, quantity, unit_price, total_price 
                        FROM invoice_items 
                        WHERE transaction_id = %s 
                        ORDER BY id ASC;
                    """, (chosen_id,))
                    items_r = cur.fetchall()

                pdf_bytes = generate_receipt_pdf(tx_dict, items_r)
                st.download_button("تحميل وثيقة السند (PDF)", data=pdf_bytes, file_name=f"Voucher_{chosen_id}.pdf", mime="application/pdf", icon=":material/download:")

    with tab_ex:
        df_all_tx = run_query("""
            SELECT t.id AS "رقم الفاتورة", t.tx_date AS "التاريخ", t.tx_type AS "نوع الحركة", 
                   p.name AS "المشروع", s.name AS "الطرف", t.amount AS "المبلغ", t.currency AS "العملة", 
                   t.amount_usd AS "المعادل بالدولار ($)", t.direction AS "الاتجاه", 
                   t.payment_method AS "طريقة الدفع", t.fx_gain_loss AS "فروقات الصرف", t.description AS "البيان"
            FROM transactions t 
            LEFT JOIN projects p ON t.project_id = p.id 
            LEFT JOIN stakeholders s ON t.stakeholder_id = s.id 
            ORDER BY t.tx_date DESC;
        """)
        st.download_button("تصدير السجل المالي العام (Excel)", data=to_excel_download_link(df_all_tx, "Transactions_Report.xlsx"), file_name="MA_Transactions.xlsx", icon=":material/table_view:")

def render_transactions_ledger():
    st.subheader(":material/receipt_long: دفتر الحركات وسجل الفواتير التفصيلي")
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
               CASE WHEN ii.affects_inventory THEN 'نعم' ELSE 'لا' END AS "خصم مخزني",
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
    st.download_button("تصدير السجل التفصيلي (Excel)", data=to_excel_download_link(df_unified, "Detailed_Ledger.xlsx"), file_name="Detailed_Ledger.xlsx", icon=":material/table_view:")

def render_add_invoice(current_user):
    if current_user['role'] in ["Admin", "Accountant"]:
        st.subheader(":material/post_add: قيد فاتورة / حركة مالية")
        projs = run_query("SELECT id, name FROM projects WHERE project_type != 'Factory' ORDER BY name;")
        parties = run_query("SELECT id, name FROM stakeholders ORDER BY name;")
        
        df_available_stock = run_query("SELECT item_name, quantity_on_hand, avg_unit_cost FROM inventory_stock ORDER BY item_name;")
        stock_item_names = df_available_stock['item_name'].tolist() if not df_available_stock.empty else []
        
        auto_inv = get_next_invoice_id()
        mode = st.radio("نمط القيد المالي:", ["سند مالي مباشر (بدون بنود تفصيلية)", "فاتورة تفصيلية متعددة البنود"])

        if "بدون بنود" in mode:
            with st.form("simple_tx_form", clear_on_submit=True):
                ca1, ca2, ca3 = st.columns(3)
                with ca1:
                    st.text_input("رقم السند", value=auto_inv, disabled=True)
                    t_date = st.date_input("التاريخ", datetime.now().date())
                    t_type = st.selectbox(
                        "نوع الحركة", 
                        ["دفعة لمشروع", "مقبوضات من مستثمر", "مصروف عام", "راتب او سلفة", "توزيع أرباح شريك", "ايراد عام"],
                        index=None,
                        placeholder="اختر نوع الحركة..."
                    )
                with ca2:
                    p_name = st.selectbox("المشروع", projs['name'].tolist(), index=None, placeholder="اختر المشروع...")
                    part_name = st.selectbox("الطرف", parties['name'].tolist(), index=None, placeholder="اختر الطرف...")
                    method = st.selectbox("طريقة الدفع", ["كاش (نقداً)", "حوالة مصرفية", "شيك بنكي"], index=None, placeholder="اختر طريقة الدفع...")
                with ca3:
                    curr_choice = st.selectbox("العملة", ["USD", "SYP"], index=None, placeholder="اختر العملة...")
                    rate_val = st.number_input("سعر الصرف", min_value=1.0, value=None, placeholder="أدخل سعر الصرف...", step=0.5)
                    amount_val = st.number_input("المبلغ الإجمالي", min_value=0.0, value=None, placeholder="0.00", step=50.0)

                desc_val = st.text_area("البيان والملاحظات", placeholder="أدخل البيان والتفاصيل...")
                
                if st.form_submit_button("حفظ وترحيل السند المالي", icon=":material/save:"):
                    a_val = float(amount_val or 0.0)
                    r_val = float(rate_val or 1.0)
                    if not p_name or not part_name or not t_type or not curr_choice or not method or a_val <= 0 or rate_val is None:
                        st.error("يرجى تعبئة كافة الحقول وتحديد المشروع والطرف والعملة وسعر الصرف والمبلغ.")
                    else:
                        p_id = int(projs.loc[projs['name'] == p_name, 'id'].values[0])
                        s_id = int(parties.loc[parties['name'] == part_name, 'id'].values[0])
                        v_id = 1 if curr_choice == 'USD' else 2
                        dir_m = 'IN' if any(k in t_type for k in ['مقبوضات', 'ايراد']) else 'OUT'
                        amt_u = float(a_val if curr_choice == 'USD' else (a_val / r_val))
                        with get_db_cursor(commit=True) as (cur, _):
                            cur.execute("""
                                INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                            """, (str(auto_inv), t_date, str(t_type), p_id, s_id, v_id, a_val, curr_choice, r_val, amt_u, dir_m, method, desc_val or ""))
                        st.success(f"تم ترحيل السند {auto_inv} بنجاح.")
                        st.rerun()

        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.text_input("رقم الفاتورة", value=auto_inv, disabled=True)
                t_date_m = st.date_input("التاريخ", datetime.now().date())
            with c2:
                p_name_m = st.selectbox("المشروع", projs['name'].tolist(), index=None, placeholder="اختر المشروع...", key="multi_inv_proj")
                t_type_m = st.selectbox("نوع الحركة", ["دفعة لمشروع", "شراء مواد وتخزين", "مصروف عام", "ايراد عام"], index=None, placeholder="اختر نوع الحركة...", key="multi_inv_type")
            with c3:
                curr_m = st.selectbox("العملة", ["USD", "SYP"], index=None, placeholder="اختر العملة...", key="multi_inv_curr")
                rate_m = st.number_input("سعر الصرف", min_value=1.0, value=None, placeholder="أدخل سعر الصرف...", step=0.5, key="multi_inv_rate")
                method_m = st.selectbox("طريقة الدفع", ["كاش (نقداً)", "حوالة مصرفية", "شيك بنكي"], index=None, placeholder="اختر طريقة الدفع...", key="multi_inv_method")

            desc_m = st.text_input("البيان العام", placeholder="أدخل البيان العام للفاتورة...", key="multi_inv_desc")
            cats = ["مواد بناء وتأسيس", "إكساء وتشطيب", "أجور معلمين", "أدوات ومعدات", "نقل وشحن", "أخرى"]
            p_list = parties['name'].tolist()

            default_df = pd.DataFrame([{
                "اسم البند": "", 
                "التصنيف": None, 
                "الكمية": None, 
                "السعر الإفرادي": None, 
                "الطرف المستفيد": None, 
                "خصم من المخزون تلقائياً": False
            }])
            
            edited_df = st.data_editor(
                default_df, 
                num_rows="dynamic", 
                use_container_width=True,
                column_config={
                    "اسم البند": st.column_config.TextColumn("اسم البند / المادة (يطابق المخزون)", required=True),
                    "التصنيف": st.column_config.SelectboxColumn("التصنيف", options=cats, required=True),
                    "الكمية": st.column_config.NumberColumn("الكمية", min_value=0.01, default=None),
                    "السعر الإفرادي": st.column_config.NumberColumn("السعر الإفرادي", min_value=0.0, default=None),
                    "الطرف المستفيد": st.column_config.SelectboxColumn("الطرف المستفيد", options=p_list, required=True),
                    "خصم من المخزون تلقائياً": st.column_config.CheckboxColumn("خصم مخزني", default=False)
                }
            )

            valid_items = edited_df[
                (edited_df["اسم البند"].astype(str).str.strip() != "") & 
                (edited_df["الطرف المستفيد"].notna()) &
                (edited_df["التصنيف"].notna()) &
                (edited_df["الكمية"].notna()) &
                (edited_df["السعر الإفرادي"].notna())
            ].copy()

            if not valid_items.empty:
                valid_items["المجموع"] = valid_items["الكمية"].astype(float) * valid_items["السعر الإفرادي"].astype(float)
                total_computed = float(valid_items["المجموع"].sum())
                curr_symbol = curr_m if curr_m else ""
                st.markdown(f"### الإجمالي المحتسب: **{total_computed:,.2f} {curr_symbol}**")

                if st.button("حفظ الفاتورة ومعالجة قيود المخزون", icon=":material/save:"):
                    r_val_m = float(rate_m or 1.0)
                    if not p_name_m or not t_type_m or not curr_m or not method_m or rate_m is None or total_computed <= 0:
                        st.error("يرجى تحديد المشروع، نوع الحركة، العملة، سعر الصرف، طريقة الدفع، والتأكد من البنود.")
                    else:
                        p_id = int(projs.loc[projs['name'] == p_name_m, 'id'].values[0])
                        v_id = 1 if curr_m == 'USD' else 2
                        dir_m = 'IN' if any(k in t_type_m for k in ['مقبوضات', 'ايراد']) else 'OUT'
                        amt_u = float(total_computed if curr_m == 'USD' else (total_computed / r_val_m))
                        first_party = valid_items.iloc[0]["الطرف المستفيد"]
                        primary_s_id = int(parties.loc[parties['name'] == first_party, 'id'].values[0])

                        try:
                            with get_db_cursor(commit=True) as (cur, _):
                                cur.execute("""
                                    INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                                """, (str(auto_inv), t_date_m, str(t_type_m), p_id, primary_s_id, v_id, total_computed, curr_m, r_val_m, amt_u, dir_m, method_m, desc_m or ""))
                                
                                for _, r in valid_items.iterrows():
                                    i_name = str(r["اسم البند"]).strip()
                                    i_qty = float(r["الكمية"])
                                    i_price = float(r["السعر الإفرادي"])
                                    i_tot = float(r["المجموع"])
                                    i_party = r["الطرف المستفيد"]
                                    i_stk_id = int(parties.loc[parties['name'] == i_party, 'id'].values[0])
                                    affects_inv = bool(r.get("خصم من المخزون تلقائياً", False))

                                    if affects_inv:
                                        cur.execute("""
                                            SELECT quantity_on_hand, avg_unit_cost 
                                            FROM inventory_stock 
                                            WHERE item_name = %s 
                                            FOR UPDATE;
                                        """, (i_name,))
                                        stock_record = cur.fetchone()

                                        if not stock_record:
                                            raise ValueError(f"المادة '{i_name}' غير مسجلة في المخزون.")
                                        
                                        available_qty = float(stock_record[0])
                                        unit_cost_val = float(stock_record[1])

                                        if available_qty < i_qty:
                                            raise ValueError(f"عجز مخزني في المادة '{i_name}'. المتاح: {available_qty}، المطلوب: {i_qty}")

                                        cur.execute("""
                                            UPDATE inventory_stock 
                                            SET quantity_on_hand = quantity_on_hand - %s 
                                            WHERE item_name = %s;
                                        """, (i_qty, i_name))

                                        cur.execute("""
                                            INSERT INTO inventory_issues (transaction_id, item_name, project_id, quantity, unit_cost)
                                            VALUES (%s, %s, %s, %s, %s);
                                        """, (str(auto_inv), i_name, p_id, i_qty, unit_cost_val))

                                    cur.execute("""
                                        INSERT INTO invoice_items (transaction_id, item_name, category, quantity, unit_price, total_price, stakeholder_id, currency, affects_inventory)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                                    """, (str(auto_inv), i_name, str(r["التصنيف"]), i_qty, i_price, i_tot, i_stk_id, curr_m, affects_inv))

                            st.success(f"تم ترحيل الفاتورة {auto_inv} وتحديث الأرصدة بنجاح.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"تم التراجع عن القيد (Rollback): {e}")

def render_edit_transactions(current_user):
    if current_user['role'] in ["Admin", "Accountant"]:
        st.subheader(":material/edit_note: استعراض وإلغاء القيود المالية")
        all_tx = run_query("SELECT id, tx_date, amount, currency, description FROM transactions ORDER BY tx_date DESC LIMIT 50;")
        if not all_tx.empty:
            sel_str = st.selectbox(
                "اختر السند / الفاتورة المراد إلغاؤها:", 
                [f"{r['id']} | {r['tx_date']} | {r['amount']} {r['currency']} | {r['description']}" for _, r in all_tx.iterrows()],
                index=None,
                placeholder="اختر السند..."
            )
            if sel_str:
                sel_id = sel_str.split(" | ")[0]
                if st.button(f"حذف الفاتورة {sel_id} واسترجاع المخزون", icon=":material/delete:"):
                    try:
                        with get_db_cursor(commit=True) as (cur, _):
                            cur.execute("""
                                SELECT item_name, quantity 
                                FROM inventory_issues 
                                WHERE transaction_id = %s;
                            """, (sel_id,))
                            issued_records = cur.fetchall()

                            for it_name, it_q in issued_records:
                                cur.execute("""
                                    UPDATE inventory_stock 
                                    SET quantity_on_hand = quantity_on_hand + %s 
                                    WHERE item_name = %s;
                                """, (float(it_q), it_name))

                            cur.execute("DELETE FROM inventory_issues WHERE transaction_id = %s;", (sel_id,))
                            cur.execute("DELETE FROM invoice_items WHERE transaction_id = %s;", (sel_id,))
                            cur.execute("DELETE FROM transactions WHERE id = %s;", (sel_id,))
                        
                        st.success(f"تم حذف الفاتورة {sel_id} واستعادة قيود المخزون.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"خطأ أثناء الحذف: {e}")

def render_investor_statements():
    st.subheader(":material/manage_accounts: كشوفات حسابات المستثمرين")
    all_projs = run_query("SELECT id, name, management_fee_rate FROM projects WHERE project_type NOT IN ('Internal', 'Factory') ORDER BY name;")
    if not all_projs.empty:
        selected_proj = st.selectbox("المشروع المستهدف", all_projs['name'].tolist(), index=None, placeholder="اختر المشروع لعرض كشفه...")
        if selected_proj:
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
            with c2: st.metric("تكاليف التنفيذ", f"{costs_out:,.2f} $")
            with c3: st.metric(f"أتعاب الإدارة ({f_rate*100:.0f}%)", f"{mgmt_fee:,.2f} $")
            with c4: st.metric("الصافي المستحق", f"{net_balance:,.2f} $")

            df_inv_tx = run_query("""
                SELECT id AS "رقم الفاتورة", tx_date AS "التاريخ", tx_type AS "نوع الحركة",
                       amount AS "المبلغ", currency AS "العملة", amount_usd AS "المعادل بالدولار ($)", description AS "البيان"
                FROM transactions WHERE project_id = %s ORDER BY tx_date DESC;
            """, (p_id,))
            st.dataframe(df_inv_tx.fillna("-"), use_container_width=True, hide_index=True)

def render_projects_overview():
    st.subheader(":material/domain: كشف أتعاب الإدارة وتكاليف المشاريع")
    st.dataframe(run_query("""
        SELECT p.name AS "المشروع",
               CASE WHEN p.status = 'Active' THEN 'نشط' ELSE 'مكتمل' END AS "الحالة",
               p.management_fee_rate * 100 AS "أتعاب الإدارة %",
               COALESCE(SUM(CASE WHEN t.direction = 'OUT' THEN t.amount_usd ELSE 0 END), 0) AS "المصاريف ($)",
               ROUND(COALESCE(SUM(CASE WHEN t.direction = 'OUT' THEN t.amount_usd ELSE 0 END), 0) * p.management_fee_rate, 2) AS "أتعاب الإدارة المستحقة ($)",
               COALESCE(SUM(CASE WHEN t.direction = 'IN' THEN t.amount_usd ELSE 0 END), 0) AS "المقبوض من المستثمر ($)"
        FROM projects p 
        LEFT JOIN transactions t ON p.id = t.project_id 
        WHERE p.project_type NOT IN ('Internal', 'Factory') 
        GROUP BY p.id, p.name, p.status, p.management_fee_rate;
    """).fillna("-"), use_container_width=True, hide_index=True)
