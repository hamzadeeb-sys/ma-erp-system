import streamlit as st
from core.db import run_query, get_db_cursor
from core.auth import hash_password

def render_admin():
    st.subheader(":material/settings: لوحة الإدارة العليا وإعدادات المنظومة")
    tab_users, tab_projs = st.tabs([
        ":material/manage_accounts: إدارة المستخدمين والأمان", 
        ":material/domain_add: إضافة المشاريع والمستثمرين"
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
        sel_u_edit = st.selectbox("اختر الحساب لتعديل كلمة المرور:", all_u['username'].tolist())
        new_pass = st.text_input("كلمة المرور الجديدة", type="password")
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
                pn = st.text_input("اسم المشروع")
                pt_map = {"إكساء وتشطيب": "Finishing", "تطوير عقاري": "Development", "داخلي": "Internal"}
                pt = st.selectbox("النوع", list(pt_map.keys()))
                pf = st.number_input("أتعاب الإدارة %", min_value=0.0, value=15.0)
                if st.form_submit_button("حفظ وتفعيل المشروع", icon=":material/add_business:"):
                    if pn.strip():
                        with get_db_cursor(commit=True) as (cur, _):
                            cur.execute("INSERT INTO projects (name, project_type, management_fee_rate, status) VALUES (%s, %s, %s, 'Active') ON CONFLICT (name) DO NOTHING;", (pn.strip(), pt_map[pt], pf / 100.0))
                        st.success("تم إنشاء المشروع بنجاح.")
                        st.rerun()

        with col_p2:
            st.markdown("#### تسجيل مستثمر جديد")
            with st.form("new_inv_form", clear_on_submit=True):
                inv_name = st.text_input("اسم المستثمر")
                inv_phone = st.text_input("رقم الهاتف")
                if st.form_submit_button("تسجيل المستثمر", icon=":material/person_add:"):
                    if inv_name.strip():
                        with get_db_cursor(commit=True) as (cur, _):
                            cur.execute("INSERT INTO stakeholders (name, role, phone, status) VALUES (%s, 'Investor', %s, 'نشط') ON CONFLICT (name) DO NOTHING;", (inv_name.strip(), inv_phone.strip()))
                        st.success("تم تسجيل المستثمر بنجاح.")
                        st.rerun()
