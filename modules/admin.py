import streamlit as st
import json
from core.db import run_query, get_db_cursor
from core.auth import hash_password

def render_admin():
    st.subheader(":material/settings: لوحة الإدارة العليا وإعدادات المنظومة")
    tab_users, tab_projs, tab_audit = st.tabs([
        ":material/manage_accounts: إدارة المستخدمين والأمان", 
        ":material/domain_add: إضافة المشاريع والمستثمرين",
        ":material/security: سجل الرقابة والتدقيق (Audit Trail)"
    ])

    with tab_users:
        st.dataframe(run_query("""
            SELECT u.id AS "المعرف", u.username AS "اسم الدخول", u.full_name AS "الاسم الكامل", 
                   u.role AS "الصلاحية", COALESCE(s.name, 'غير مربوط') AS "الموظف المرتبط", 
                   CASE WHEN u.is_active THEN 'نشط' ELSE 'مجمد' END AS "الحالة"
            FROM app_users u LEFT JOIN stakeholders s ON u.stakeholder_id = s.id ORDER BY u.id ASC;
        """).fillna("-"), use_container_width=True, hide_index=True)

        st.markdown("---")
        all_u = run_query("SELECT id, username FROM app_users;")
        sel_u_edit = st.selectbox("اختر الحساب لتعديل كلمة المرور:", all_u['username'].tolist(), index=None, placeholder="اختر الحساب...")
        if sel_u_edit:
            new_pass = st.text_input("كلمة المرور الجديدة", type="password", placeholder="أدخل كلمة المرور الجديدة...")
            if st.button("تحديث كلمة المرور وتشفيرها", icon=":material/lock_reset:"):
                if new_pass.strip():
                    hashed = hash_password(new_pass.strip())
                    with get_db_cursor(commit=True) as (cur, _):
                        cur.execute("UPDATE app_users SET password = %s WHERE username = %s;", (hashed, sel_u_edit))
                    st.success(f"تم تحديث وتشفير كلمة المرور للحساب {sel_u_edit}.")

    with tab_projs:
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("#### إضافة مشروع جديد")
            with st.form("new_proj_form", clear_on_submit=True):
                pn = st.text_input("اسم المشروع", placeholder="أدخل الاسم الرسمي للمشروع...")
                pt_map = {"إكساء وتشطيب": "Finishing", "تطوير عقاري": "Development", "داخلي": "Internal"}
                pt = st.selectbox("النوع", list(pt_map.keys()), index=None, placeholder="حدد تصنيف المشروع...")
                pf = st.number_input("أتعاب الإدارة %", min_value=0.0, max_value=100.0, value=None, placeholder="0.00", step=1.0)
                if st.form_submit_button("حفظ وتفعيل المشروع", icon=":material/add_business:"):
                    if not pn or not pt or pf is None:
                        st.error("يرجى إدخال اسم المشروع، نوعه، ونسبة أتعاب الإدارة.")
                    else:
                        with get_db_cursor(commit=True) as (cur, _):
                            cur.execute("INSERT INTO projects (name, project_type, management_fee_rate, status) VALUES (%s, %s, %s, 'Active') ON CONFLICT (name) DO NOTHING;", (pn.strip(), pt_map[pt], float(pf) / 100.0))
                        st.success("تم إنشاء المشروع بنجاح.")
                        st.rerun()

        with col_p2:
            st.markdown("#### تسجيل مستثمر جديد")
            with st.form("new_inv_form", clear_on_submit=True):
                inv_name = st.text_input("اسم المستثمر", placeholder="الاسم الكامل للمستثمر...")
                inv_phone = st.text_input("رقم الهاتف", placeholder="رقم الهاتف...")
                if st.form_submit_button("تسجيل المستثمر", icon=":material/person_add:"):
                    if not inv_name.strip():
                        st.error("يرجى إدخال اسم المستثمر.")
                    else:
                        with get_db_cursor(commit=True) as (cur, _):
                            cur.execute("INSERT INTO stakeholders (name, role, phone, status) VALUES (%s, 'Investor', %s, 'نشط') ON CONFLICT (name) DO NOTHING;", (inv_name.strip(), inv_phone.strip() if inv_phone else ""))
                        st.success("تم تسجيل المستثمر بنجاح.")
                        st.rerun()

    with tab_audit:
        st.markdown("#### :material/security: سجل مراقبة التعديلات والعمليات الحساسة")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            audit_tbl_filter = st.selectbox("تصفية بحسب الجدول:", ["الكل", "transactions", "inventory_stock", "app_users", "factory_settlements"])
        with col_f2:
            audit_act_filter = st.selectbox("تصفية بحسب نوع العملية:", ["الكل", "INSERT", "UPDATE", "DELETE"])

        query_audit = "SELECT id, changed_at, table_name, action_type, record_id, changed_by, old_data, new_data FROM audit_logs WHERE 1=1"
        params = []
        if audit_tbl_filter != "الكل":
            query_audit += " AND table_name = %s"
            params.append(audit_tbl_filter)
        if audit_act_filter != "الكل":
            query_audit += " AND action_type = %s"
            params.append(audit_act_filter)
        query_audit += " ORDER BY changed_at DESC LIMIT 100;"

        df_audit = run_query(query_audit, tuple(params) if params else None)
        if not df_audit.empty:
            # عرض ملخص السجلات
            st.dataframe(
                df_audit[["id", "changed_at", "table_name", "action_type", "record_id", "changed_by"]].rename(columns={
                    "id": "رقم القيد", "changed_at": "التوقيت", "table_name": "الجدول", 
                    "action_type": "نوع الحركة", "record_id": "معرف السجل", "changed_by": "المنفّذ"
                }), 
                use_container_width=True, 
                hide_index=True
            )

            # استعراض تفاصيل حمولة JSON القديمة والجديدة
            st.markdown("##### تفاصيل سجل محدد (JSON Payload Inspection)")
            selected_audit_id = st.selectbox("اختر رقم القيد لفحص التفاصيل:", df_audit["id"].tolist())
            if selected_audit_id:
                row = df_audit[df_audit["id"] == selected_audit_id].iloc[0]
                c_old, c_new = st.columns(2)
                with c_old:
                    st.caption("البيانات قبل التعديل (OLD DATA)")
                    st.json(row["old_data"] if row["old_data"] else {})
                with c_new:
                    st.caption("البيانات بعد التعديل (NEW DATA)")
                    st.json(row["new_data"] if row["new_data"] else {})
        else:
            st.info("لا توجد سجلات تدقيق مسجلة تطابق التصفية.")
