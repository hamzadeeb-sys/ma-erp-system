import streamlit as st
from datetime import datetime, time
from core.db import run_query, get_db_cursor

def render_attendance(current_user):
    st.subheader(":material/schedule: متابعة حضور وساعات دوام الكوادر")
    emps_df = run_query("SELECT id, name FROM stakeholders WHERE role IN ('Employee', 'Partner') ORDER BY name;")

    tab_att_log, tab_att_new, tab_att_rep = st.tabs([
        ":material/badge: سجل الدوام العام", 
        ":material/add_circle: تسجيل قيد دوام", 
        ":material/analytics: ملخص الساعات والغياب"
    ])
    
    with tab_att_log:
        df_att_log = run_query("""
            SELECT a.id AS "المعرف", s.name AS "الموظف", a.work_date AS "التاريخ", 
                   a.time_in AS "وقت الحضور", a.time_out AS "وقت الانصراف", 
                   a.total_hours AS "الساعات الفعلية", a.status AS "الحالة", a.notes AS "ملاحظات"
            FROM employee_attendance a JOIN stakeholders s ON a.employee_id = s.id 
            ORDER BY a.work_date DESC;
        """)
        st.dataframe(df_att_log.fillna("-"), use_container_width=True, hide_index=True)

    with tab_att_new:
        if current_user['role'] in ["Admin", "Accountant", "Secretary"]:
            with st.form("att_form", clear_on_submit=True):
                ca1, ca2 = st.columns(2)
                with ca1:
                    sel_emp_att = st.selectbox("الموظف", emps_df['name'].tolist(), index=None, placeholder="اختر الموظف...")
                    att_date = st.date_input("التاريخ", datetime.now().date())
                    att_status = st.selectbox("الحالة", ["حاضر", "متأخر", "غياب", "إجازة"], index=None, placeholder="اختر حالة الدوام...")
                with ca2:
                    t_in = st.time_input("الدخول", time(9, 0))
                    t_out = st.time_input("الانصراف", time(17, 0))
                    att_notes = st.text_input("ملاحظات", placeholder="أدخل أية ملاحظات حول التأخير أو الإذن...")

                if st.form_submit_button("تثبيت قيد الدوام", icon=":material/save:"):
                    if not sel_emp_att or not att_status:
                        st.error("يرجى اختيار الموظف وتحديد حالة الحضور.")
                    else:
                        emp_id_val = int(emps_df.loc[emps_df['name'] == sel_emp_att, 'id'].values[0])
                        dur = 8.0 if att_status in ["حاضر", "متأخر"] else 0.0
                        with get_db_cursor(commit=True) as (cur, _):
                            cur.execute("""
                                INSERT INTO employee_attendance (employee_id, work_date, time_in, time_out, total_hours, status, notes)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (employee_id, work_date) 
                                DO UPDATE SET time_in = EXCLUDED.time_in, time_out = EXCLUDED.time_out, total_hours = EXCLUDED.total_hours, status = EXCLUDED.status, notes = EXCLUDED.notes;
                            """, (emp_id_val, att_date, t_in if dur > 0 else None, t_out if dur > 0 else None, dur, att_status, att_notes or ""))
                        st.success("تم تثبيت حركة الدوام بنجاح.")
                        st.rerun()

    with tab_att_rep:
        df_att_rep = run_query("""
            SELECT s.name AS "الموظف", 
                   COUNT(CASE WHEN a.status = 'حاضر' THEN 1 END) AS "أيام الحضور", 
                   COUNT(CASE WHEN a.status = 'غياب' THEN 1 END) AS "أيام الغياب", 
                   COALESCE(SUM(a.total_hours), 0) AS "إجمالي الساعات" 
            FROM stakeholders s 
            LEFT JOIN employee_attendance a ON s.id = a.employee_id 
            WHERE s.role IN ('Employee', 'Partner') 
            GROUP BY s.id, s.name;
        """)
        st.dataframe(df_att_rep.fillna("-"), use_container_width=True, hide_index=True)

def render_payroll(current_user):
    st.subheader(":material/payments: احتساب مسيرات الرواتب وصرف المستحقات")
    emps_sal = run_query("SELECT id, name, salary_amount, salary_currency, salary_type FROM stakeholders WHERE role IN ('Employee', 'Partner') AND salary_amount > 0;")
    if not emps_sal.empty:
        c1, c2 = st.columns(2)
        with c1: sel_emp = st.selectbox("الموظف المستهدف", emps_sal['name'].tolist(), index=None, placeholder="اختر الموظف لاحتساب راتبه...")
        with c2: p_month = st.text_input("شهر المسير (YYYY-MM)", value=datetime.now().strftime("%Y-%m"))

        if sel_emp:
            emp_row = emps_sal[emps_sal['name'] == sel_emp].iloc[0]
            emp_id = int(emp_row['id'])
            base_s = float(emp_row['salary_amount'])
            curr_db = str(emp_row['salary_currency'])
            sal_type = str(emp_row.get('salary_type', 'monthly_standard'))

            daily_div = 26.0 if sal_type == 'monthly_ex_friday' else (24.0 if sal_type == 'weekly_6days' else 30.0)
            hourly_div = daily_div * 8.0

            with get_db_cursor() as (cur, _):
                cur.execute("SELECT COALESCE(SUM(overtime_hours), 0), COUNT(CASE WHEN status = 'غياب' THEN 1 END) FROM employee_attendance WHERE employee_id = %s AND TO_CHAR(work_date, 'YYYY-MM') = %s;", (emp_id, p_month))
                att_d = cur.fetchone()
                cur.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE stakeholder_id = %s AND tx_type = 'راتب او سلفة' AND TO_CHAR(tx_date, 'YYYY-MM') = %s AND direction = 'OUT';", (emp_id, p_month))
                adv_taken = float(cur.fetchone()[0] or 0.0)

            ot_h, abs_d = float(att_d[0]), int(att_d[1])
            hourly_r = base_s / hourly_div if base_s > 0 else 0.0
            daily_r = base_s / daily_div if base_s > 0 else 0.0
            ot_val = ot_h * hourly_r * 1.5
            ded_abs = abs_d * daily_r
            total_ded = ded_abs + adv_taken
            net_s = base_s + ot_val - total_ded

            col1, col2, col3, col4, col5 = st.columns(5)
            with col1: st.metric("الراتب الأساسي", f"{base_s:,.2f} {curr_db}")
            with col2: st.metric("الإضافي المحتسب", f"+{ot_val:,.2f}")
            with col3: st.metric("خصم الغياب", f"-{ded_abs:,.2f}")
            with col4: st.metric("السلف المقتطعة", f"-{adv_taken:,.2f}")
            with col5: st.metric("صافي المستحق للصرف", f"{net_s:,.2f} {curr_db}")

            if current_user['role'] in ["Admin", "Accountant"]:
                if st.button("اعتماد وصرف المسير المالي", icon=":material/check_circle:"):
                    sal_id = f"SAL-{p_month}-{emp_id}"
                    v_id = 1 if curr_db == 'USD' else 2
                    with get_db_cursor(commit=True) as (cur, _):
                        cur.execute("SELECT exchange_rate FROM transactions WHERE currency = 'SYP' ORDER BY tx_date DESC LIMIT 1;")
                        s_rate_row = cur.fetchone()
                        s_rate = float(s_rate_row[0]) if s_rate_row else 131.0
                        amt_u = net_s if curr_db == 'USD' else (net_s / s_rate)

                        if net_s > 0:
                            cur.execute("INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description) VALUES (%s, CURRENT_DATE, 'راتب او سلفة', 2, %s, %s, %s, %s, %s, %s, 'OUT', 'كاش', %s);", (sal_id, emp_id, v_id, net_s, curr_db, s_rate if curr_db == 'SYP' else 1.0, amt_u, f"صرف صافي راتب شهر {p_month}"))
                        cur.execute("INSERT INTO payroll_records (employee_id, payroll_month, base_salary, overtime_hours, overtime_amount, absence_days, deductions, net_salary, currency, payment_status, transaction_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'معتمد', %s);", (emp_id, p_month, base_s, ot_h, ot_val, abs_d, total_ded, net_s, curr_db, sal_id))
                    st.success("تم صرف المسير وترحيل السند المحاسبي.")
                    st.rerun()

def render_employee_portal(current_user):
    st.subheader(f":material/account_circle: السجل المالي والدوام الذاتي: {current_user['full_name']}")
    emp_s_id = current_user.get("stakeholder_id")
    if not emp_s_id:
        st.warning("هذا الحساب غير مربوط بملف موظف. يرجى مراجعة إدارة النظام.")
    else:
        with get_db_cursor() as (cur, _):
            cur.execute("SELECT name, salary_amount, salary_currency FROM stakeholders WHERE id = %s;", (emp_s_id,))
            emp_meta = cur.fetchone()
            cur.execute("SELECT COALESCE(SUM(amount), 0), COUNT(id) FROM transactions WHERE stakeholder_id = %s AND direction = 'OUT';", (emp_s_id,))
            out_fin = cur.fetchone()

        base_sal = float(emp_meta[1] or 0.0)
        curr_sal = "دولار ($)" if emp_meta and emp_meta[2] == 'USD' else "ليرة سورية"
        tot_received = float(out_fin[0] or 0.0)

        c1, c2 = st.columns(2)
        with c1: st.metric("الراتب الأساسي المسجل", f"{base_sal:,.2f} {curr_sal}")
        with c2: st.metric("إجمالي الدفعات المقبوضة", f"{tot_received:,.2f} {curr_sal}")

        st.markdown("---")
        tab1, tab2 = st.tabs([":material/receipt_long: السندات المقبوضة", ":material/schedule: سجل الحضور والدوام"])
        with tab1:
            st.dataframe(run_query("""
                SELECT id AS "رقم السند", tx_date AS "التاريخ", tx_type AS "نوع الحركة", 
                       amount AS "المبلغ", currency AS "العملة", payment_method AS "طريقة الدفع", description AS "البيان"
                FROM transactions WHERE stakeholder_id = %s ORDER BY tx_date DESC;
            """, (emp_s_id,)).fillna("-"), use_container_width=True, hide_index=True)
        with tab2:
            st.dataframe(run_query("""
                SELECT work_date AS "التاريخ", time_in AS "الحضور", time_out AS "الانصراف", 
                       total_hours AS "ساعات العمل", status AS "الحالة", notes AS "ملاحظات"
                FROM employee_attendance WHERE employee_id = %s ORDER BY work_date DESC;
            """, (emp_s_id,)).fillna("-"), use_container_width=True, hide_index=True)
