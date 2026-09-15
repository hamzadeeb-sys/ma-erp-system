import streamlit as st
from datetime import datetime
from core.db import run_query, get_db_cursor

def render_inventory(current_user):
    st.subheader("📦 مستودع ومخزون مواد المشاريع")
    tab_st, tab_iss = st.tabs(["🧱 جرد المواد", "📤 صرف مادة إلى مشروع"])
    with tab_st:
        st.dataframe(run_query("""
            SELECT item_name AS "المادة / الصنف", category AS "التصنيف", 
                   quantity_on_hand AS "الرصيد المتوفر", avg_unit_cost AS "التكلفة الإفرادية", currency AS "العملة"
            FROM inventory_stock ORDER BY quantity_on_hand DESC;
        """).fillna("-"), use_container_width=True, hide_index=True)

    with tab_iss:
        if current_user['role'] in ["Admin", "Accountant"]:
            df_mats = run_query("SELECT item_name, quantity_on_hand, avg_unit_cost, currency FROM inventory_stock WHERE quantity_on_hand > 0;")
            df_p = run_query("SELECT id, name FROM projects WHERE status = 'Active' AND project_type NOT IN ('Internal', 'Factory');")
            if not df_mats.empty and not df_p.empty:
                with st.form("iss_mat_form"):
                    sel_mat = st.selectbox("المادة", df_mats['item_name'].tolist())
                    mat_inf = df_mats[df_mats['item_name'] == sel_mat].iloc[0]
                    sel_p = st.selectbox("المشروع المستلم", df_p['name'].tolist())
                    iss_q = st.number_input("الكمية", min_value=0.01, max_value=float(mat_inf['quantity_on_hand']), value=1.0)
                    if st.form_submit_button("🚀 اعتماد الصرف المخزني"):
                        p_id = int(df_p.loc[df_p['name'] == sel_p, 'id'].values[0])
                        tot = iss_q * float(mat_inf['avg_unit_cost'])
                        with get_db_cursor(commit=True) as (cur, _):
                            cur.execute("UPDATE inventory_stock SET quantity_on_hand = quantity_on_hand - %s WHERE item_name = %s;", (iss_q, sel_mat))
                            cur.execute("INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description) VALUES (%s, CURRENT_DATE, 'صرف مواد من المخزون', %s, 1, 1, %s, %s, 1.0, %s, 'OUT', 'صرف مخزني', %s);", (f"MAT-{int(datetime.now().timestamp())}", p_id, tot, mat_inf['currency'], tot, f"صرف {iss_q} من {sel_mat}"))
                        st.success("تم صرف المادة وتحديث رصيد المستودع.")
                        st.rerun()

def render_stakeholders(current_user):
    st.subheader("👥 دليل الشركاء والموظفين والجهات الخارجية")
    tab_list, tab_stk_ledger, tab_add_ext = st.tabs(["📋 القائمة وتعديل البيانات", "🔍 كشف الحركات التفصيلي", "➕ تسجيل جهة جديدة"])

    with tab_list:
        st.dataframe(run_query("""
            SELECT id AS "المعرف", name AS "الاسم", role AS "الدور", salary_amount AS "الراتب", 
                   salary_currency AS "العملة", salary_type AS "نظام الدوام", phone AS "الهاتف"
            FROM stakeholders ORDER BY id ASC;
        """).fillna("-"), use_container_width=True, hide_index=True)

        st.markdown("---")
        all_stk = run_query("SELECT id, name FROM stakeholders ORDER BY name;")
        if not all_stk.empty:
            chosen_stk_name = st.selectbox("اختر الطرف للتعديل:", [""] + all_stk['name'].tolist())
            if chosen_stk_name:
                with get_db_cursor() as (cur, _):
                    cur.execute("SELECT id, name, role, salary_amount, salary_currency, salary_type, phone, notes FROM stakeholders WHERE name = %s;", (chosen_stk_name,))
                    stk_rec = cur.fetchone()

                roles_map = {"موظف": "Employee", "جهة تعامل": "General", "مستثمر": "Investor", "شريك": "Partner"}
                roles_keys = list(roles_map.keys())
                curr_role_idx = [i for i, k in enumerate(roles_keys) if roles_map[k] == stk_rec[2]]

                with st.form("edit_stk_form"):
                    ed_name = st.text_input("الاسم الكامل", value=stk_rec[1])
                    ed_role = st.selectbox("الدور", roles_keys, index=curr_role_idx[0] if curr_role_idx else 0)
                    ed_sal = st.number_input("الراتب", min_value=0.0, value=float(stk_rec[3] or 0.0))
                    ed_curr = st.selectbox("عملة الراتب", ["USD", "SYP"], index=0 if stk_rec[4] == 'USD' else 1)
                    ed_phone = st.text_input("الهاتف", value=stk_rec[6] or "")
                    ed_notes = st.text_area("ملاحظات", value=stk_rec[7] or "")

                    if st.form_submit_button("💾 حفظ التعديلات"):
                        with get_db_cursor(commit=True) as (cur, _):
                            cur.execute("UPDATE stakeholders SET name = %s, role = %s, salary_amount = %s, salary_currency = %s, phone = %s, notes = %s WHERE id = %s;", (ed_name.strip(), roles_map[ed_role], ed_sal, ed_curr, ed_phone.strip(), ed_notes.strip(), stk_rec[0]))
                        st.success("تم تحديث البيانات.")
                        st.rerun()

    with tab_stk_ledger:
        all_stks_v = run_query("SELECT id, name FROM stakeholders ORDER BY name;")
        if not all_stks_v.empty:
            sel_ledger = st.selectbox("اختر الطرف لعرض كشفه:", all_stks_v['name'].tolist())
            t_id = int(all_stks_v.loc[all_stks_v['name'] == sel_ledger, 'id'].values[0])
            st.dataframe(run_query("""
                SELECT t.id AS "رقم الفاتورة", t.tx_date AS "التاريخ", t.tx_type AS "نوع الحركة", 
                       t.amount AS "المبلغ", t.currency AS "العملة", t.payment_method AS "طريقة الدفع", t.description AS "البيان"
                FROM transactions t WHERE t.stakeholder_id = %s ORDER BY t.tx_date DESC;
            """, (t_id,)).fillna("-"), use_container_width=True, hide_index=True)

    with tab_add_ext:
        if current_user['role'] in ["Admin", "Accountant"]:
            with st.form("add_ext_form", clear_on_submit=True):
                p_name = st.text_input("الاسم الكامل / اسم الجهة")
                p_cat = st.selectbox("التصنيف", ["مورد مواد", "معمل تصنيع", "شحن ونقل", "استشارات", "أخرى"])
                p_phone = st.text_input("رقم الهاتف")
                p_notes = st.text_area("ملاحظات")
                if st.form_submit_button("🚀 تسجيل الجهة"):
                    if p_name.strip():
                        with get_db_cursor(commit=True) as (cur, _):
                            cur.execute("INSERT INTO stakeholders (name, role, phone, notes) VALUES (%s, 'General', %s, %s) ON CONFLICT (name) DO NOTHING;", (p_name.strip(), p_phone.strip(), f"[{p_cat}] {p_notes.strip()}"))
                        st.success("تم تسجيل الجهة بنجاح.")
                        st.rerun()

def render_appointments(current_user):
    st.subheader("📅 سجل المواعيد وزيارات المكتب")
    tab_v_list, tab_v_new = st.tabs(["📋 جدول الزيارات", "➕ تسجيل زيارة / موعد"])

    with tab_v_list:
        cv1, cv2 = st.columns(2)
        with cv1: filter_v_type = st.selectbox("تصفية بحسب النوع", ["الكل", "موعد مسبق", "زيارة فورية"])
        with cv2: filter_v_status = st.selectbox("تصفية بحسب الحالة", ["الكل", "قيد الانتظار", "جارية", "مكتملة", "ملغية"])

        query_appts = "SELECT id AS \"رقم القيد\", visitor_name AS \"الزائر\", visitor_phone AS \"الهاتف\", visit_type AS \"النوع\", visit_date AS \"التاريخ\", visit_time AS \"الوقت\", host_person AS \"الشخص المطلوب\", purpose AS \"الغاية\", status AS \"الحالة\", recorded_by AS \"المسجل\", notes AS \"ملاحظات\" FROM office_appointments WHERE 1=1"
        params = []
        if filter_v_type != "الكل":
            query_appts += " AND visit_type = %s"
            params.append(filter_v_type)
        if filter_v_status != "الكل":
            query_appts += " AND status = %s"
            params.append(filter_v_status)
        query_appts += " ORDER BY visit_date DESC, visit_time DESC;"
        st.dataframe(run_query(query_appts, tuple(params) if params else None).fillna("-"), use_container_width=True, hide_index=True)

    with tab_v_new:
        if current_user['role'] in ["Admin", "Secretary"]:
            with st.form("new_visit_form", clear_on_submit=True):
                ca1, ca2 = st.columns(2)
                with ca1:
                    v_name = st.text_input("اسم الزائر / الجهة")
                    v_phone = st.text_input("رقم الهاتف")
                    v_type = st.selectbox("نوع الزيارة", ["زيارة فورية", "موعد مسبق"])
                    v_date = st.date_input("التاريخ", datetime.now().date())
                with ca2:
                    v_time = st.time_input("الوقت", datetime.now().time())
                    v_host = st.selectbox("الشخص المطلوب مقابلته", ["المدير العام", "حمزة ديب", "مصعب المصري", "سامر ديب", "محاسب الشركة", "آخر"])
                    v_purpose = st.text_input("الغاية من الزيارة")
                    v_status = st.selectbox("الحالة", ["قيد الانتظار", "جارية", "مكتملة", "ملغية"])
                v_notes = st.text_area("ملاحظات إضافية")

                if st.form_submit_button("💾 حفظ الموعد"):
                    if v_name.strip():
                        with get_db_cursor(commit=True) as (cur, _):
                            cur.execute("INSERT INTO office_appointments (visitor_name, visitor_phone, visit_type, visit_date, visit_time, host_person, purpose, status, notes, recorded_by) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);", (v_name.strip(), v_phone.strip(), v_type, v_date, v_time, v_host, v_purpose.strip(), v_status, v_notes.strip(), current_user['full_name']))
                        st.success("تم تسجيل الموعد بنجاح.")
                        st.rerun()
