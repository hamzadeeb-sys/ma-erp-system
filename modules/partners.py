import streamlit as st
import pandas as pd
from datetime import datetime
from core.db import run_query, get_db_cursor
from core.utils import to_excel_download_link

def render_partners(current_user):
    st.subheader(":material/handshake: منظومة حسابات وتسوية الشركاء الموحدة")
    tab_equity, tab_recon = st.tabs([
        ":material/pie_chart: هيكل رأس المال والملكيات",
        ":material/account_balance_wallet: كشف الحساب الموحد ومطابقة المسحوبات"
    ])

    with get_db_cursor() as (cur, _):
        # 1. إجمالي أتعاب إدارة المشاريع التراكمية
        cur.execute("""
            SELECT COALESCE(SUM(ROUND(t.amount_usd * p.management_fee_rate, 2)), 0)
            FROM projects p JOIN transactions t ON p.id = t.project_id
            WHERE t.direction = 'OUT' AND p.project_type NOT IN ('Internal', 'Factory');
        """)
        total_company_profit = float(cur.fetchone()[0] or 0.0)

        # 2. بيانات حصة حمزة ديب الإدارية المحمية
        cur.execute("SELECT id, partner_equity_pct, salary_amount, salary_currency FROM stakeholders WHERE name = 'حمزة ديب';")
        h_data = cur.fetchone()
        hamza_id = int(h_data[0]) if h_data else 1
        hamza_pct = float(h_data[1]) if (h_data and h_data[1] is not None and float(h_data[1]) > 0) else 15.00
        hamza_sal = float(h_data[2]) if (h_data and h_data[2] is not None) else 0.00

        # 3. رؤوس الأموال التأسيسية
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

        cur.execute("SELECT id FROM stakeholders WHERE name = 'مصعب المصري';")
        r_mosab = cur.fetchone()
        mosab_id = int(r_mosab[0]) if r_mosab else 2

        cur.execute("SELECT id FROM stakeholders WHERE name = 'سامر ديب';")
        r_samer = cur.fetchone()
        samer_id = int(r_samer[0]) if r_samer else 3

        # 4. أرباح معمل الحجر المحققة لمصعب المصري (حصة الشركة 25%)
        cur.execute("SELECT COALESCE(SUM(company_share_usd), 0) FROM factory_settlements;")
        mosab_factory_profit = float(cur.fetchone()[0] or 0.0)

    total_financial_capital = mosab_capital + samer_capital
    remaining_equity = max(0.0, 100.0 - hamza_pct)
    mosab_pct = (mosab_capital / total_financial_capital * remaining_equity) if total_financial_capital > 0 else remaining_equity
    samer_pct = (samer_capital / total_financial_capital * remaining_equity) if total_financial_capital > 0 else 0.0

    # الأرباح المستحقة من أتعاب إدارة المشاريع
    mosab_mgmt_share = (total_company_profit * mosab_pct / 100.0)
    samer_mgmt_share = (total_company_profit * samer_pct / 100.0)
    hamza_mgmt_share = (total_company_profit * hamza_pct / 100.0)

    # إجمالي استحقاقات كل شريك
    mosab_total_earned = mosab_mgmt_share + mosab_factory_profit
    samer_total_earned = samer_mgmt_share
    hamza_total_earned = hamza_mgmt_share

    # احتساب إجمالي المسحوبات الفعلية لكل شريك من جميع الصناديق والمشاريع
    with get_db_cursor() as (cur, _):
        cur.execute("""
            SELECT COALESCE(SUM(amount_usd), 0) 
            FROM transactions 
            WHERE stakeholder_id = %s 
              AND tx_type IN ('توزيع أرباح شريك', 'راتب او سلفة') 
              AND direction = 'OUT';
        """, (mosab_id,))
        mosab_withdrawals = float(cur.fetchone()[0] or 0.0)

        cur.execute("""
            SELECT COALESCE(SUM(amount_usd), 0) 
            FROM transactions 
            WHERE stakeholder_id = %s 
              AND tx_type IN ('توزيع أرباح شريك', 'راتب او سلفة') 
              AND direction = 'OUT';
        """, (samer_id,))
        samer_withdrawals = float(cur.fetchone()[0] or 0.0)

        cur.execute("""
            SELECT COALESCE(SUM(amount_usd), 0) 
            FROM transactions 
            WHERE stakeholder_id = %s 
              AND tx_type IN ('توزيع أرباح شريك', 'راتب او سلفة') 
              AND direction = 'OUT';
        """, (hamza_id,))
        hamza_withdrawals = float(cur.fetchone()[0] or 0.0)

    # الصافي النهائي لكل شريك: موجب = مستحق للشريك (دائن) | سالب = بذمة الشريك للشركة (مدين)
    mosab_net_balance = mosab_total_earned - mosab_withdrawals
    samer_net_balance = samer_total_earned - samer_withdrawals
    hamza_net_balance = hamza_total_earned - hamza_withdrawals

    with tab_equity:
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f'<div class="metric-card"><div class="metric-title">رأس المال التأسيسي الإجمالي</div><div class="metric-value-usd">{total_financial_capital:,.2f} $</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="metric-card"><div class="metric-title">أتعاب الإدارة المتراكمة</div><div class="metric-value-gold">{total_company_profit:,.2f} $</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="metric-card"><div class="metric-title">حصة حمزة ديب الإدارية المحمية</div><div class="metric-value-usd" style="color: #BE9D5F;">{hamza_pct:.2f}%</div></div>', unsafe_allow_html=True)

        partners_breakdown = [
            {"الشريك": "مصعب المصري", "الصفة": "مؤسس وشريك مالي وإداري", "المساهمة": f"{mosab_capital:,.2f} $", "نسبة رأس المال": f"{(mosab_capital/total_financial_capital*100 if total_financial_capital else 0):.1f}%", "نسبة الملكية المعتمدة": f"{mosab_pct:.2f}%", "الأرباح المستحقة ($)": f"{mosab_total_earned:,.2f} $"},
            {"الشريك": "سامر ديب", "الصفة": "مساهم وشريك مالي", "المساهمة": f"{samer_capital:,.2f} $", "نسبة رأس المال": f"{(samer_capital/total_financial_capital*100 if total_financial_capital else 0):.1f}%", "نسبة الملكية المعتمدة": f"{samer_pct:.2f}%", "الأرباح المستحقة ($)": f"{samer_total_earned:,.2f} $"},
            {"الشريك": "حمزة ديب", "الصفة": "شريك إداري ومسؤول تقني", "المساهمة": "0.00 $", "نسبة رأس المال": "0.0%", "نسبة الملكية المعتمدة": f"{hamza_pct:.2f}%", "الأرباح المستحقة ($)": f"{hamza_total_earned:,.2f} $"}
        ]
        st.dataframe(pd.DataFrame(partners_breakdown), use_container_width=True, hide_index=True)

        if current_user['role'] == "Admin":
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### :material/tune: تحديث النسبة والبيانات المالية لحمزة ديب")
            with st.form("update_hamza_form"):
                col_h1, col_h2 = st.columns(2)
                with col_h1: 
                    new_h_pct = st.number_input("النسبة % من الأرباح", min_value=1.0, max_value=50.0, value=float(hamza_pct), step=1.0)
                with col_h2: 
                    new_h_sal = st.number_input("الراتب الشهري الثابت", min_value=0.0, value=float(hamza_sal), step=50.0)
                if st.form_submit_button("حفظ التعديلات المعتمدة", icon=":material/save:"):
                    with get_db_cursor(commit=True) as (cur, _):
                        cur.execute("UPDATE stakeholders SET partner_equity_pct = %s, salary_amount = %s WHERE name = 'حمزة ديب';", (new_h_pct, new_h_sal))
                    st.success("تم تحديث البيانات المالية بنجاح.")
                    st.rerun()

    with tab_recon:
        st.markdown("#### :material/balance: جدول المطابقة والتسوية الختامية للشركاء")
        st.caption("مقارنة الأرباح المحققة مع إجمالي المسحوبات النقدية من كافة الصناديق لتحديد المركز المالي الصافي:")

        recon_data = [
            {
                "الشريك": "مصعب المصري",
                "أرباح المشاريع ($)": f"{mosab_mgmt_share:,.2f}",
                "أرباح المعمل ($)": f"{mosab_factory_profit:,.2f}",
                "إجمالي الاستحقاق ($)": f"{mosab_total_earned:,.2f}",
                "إجمالي المسحوبات ($)": f"{mosab_withdrawals:,.2f}",
                "الرصيد الصافي ($)": f"{mosab_net_balance:,.2f}",
                "المركز المالي": "دائن (مستحق للشريك) 🟢" if mosab_net_balance >= 0 else "مدين (مترتب بذمته) 🔴"
            },
            {
                "الشريك": "سامر ديب",
                "أرباح المشاريع ($)": f"{samer_mgmt_share:,.2f}",
                "أرباح المعمل ($)": "0.00",
                "إجمالي الاستحقاق ($)": f"{samer_total_earned:,.2f}",
                "إجمالي المسحوبات ($)": f"{samer_withdrawals:,.2f}",
                "الرصيد الصافي ($)": f"{samer_net_balance:,.2f}",
                "المركز المالي": "دائن (مستحق للشريك) 🟢" if samer_net_balance >= 0 else "مدين (مترتب بذمته) 🔴"
            },
            {
                "الشريك": "حمزة ديب",
                "أرباح المشاريع ($)": f"{hamza_mgmt_share:,.2f}",
                "أرباح المعمل ($)": "0.00",
                "إجمالي الاستحقاق ($)": f"{hamza_total_earned:,.2f}",
                "إجمالي المسحوبات ($)": f"{hamza_withdrawals:,.2f}",
                "الرصيد الصافي ($)": f"{hamza_net_balance:,.2f}",
                "المركز المالي": "دائن (مستحق للشريك) 🟢" if hamza_net_balance >= 0 else "مدين (مترتب بذمته) 🔴"
            }
        ]

        df_recon = pd.DataFrame(recon_data)
        st.dataframe(df_recon, use_container_width=True, hide_index=True)
        st.download_button(
            "تصدير كشف مطابقة الشركاء (Excel)",
            data=to_excel_download_link(df_recon, "Partners_Reconciliation.xlsx"),
            file_name="MA_Partners_Reconciliation.xlsx",
            icon=":material/table_view:"
        )

        st.markdown("---")
        st.markdown("##### :material/history: كشف السحوبات التفصيلي لكل شريك")
        partner_choice = st.selectbox("اختر الشريك لاستعراض قيود سحوباته المباشرة:", ["مصعب المصري", "سامر ديب", "حمزة ديب"])
        chosen_partner_id = mosab_id if partner_choice == "مصعب المصري" else (samer_id if partner_choice == "سامر ديب" else hamza_id)

        df_partner_tx = run_query("""
            SELECT t.id AS "رقم السند", t.tx_date AS "التاريخ", t.tx_type AS "نوع القيد",
                   p.name AS "المشروع المصروف منه", v.name AS "الصندوق",
                   t.amount AS "المبلغ بالعملة الأصلية", t.currency AS "العملة",
                   t.amount_usd AS "المعادل بالدولار ($)", t.description AS "البيان"
            FROM transactions t
            LEFT JOIN projects p ON t.project_id = p.id
            LEFT JOIN vaults v ON t.vault_id = v.id
            WHERE t.stakeholder_id = %s AND t.direction = 'OUT'
            ORDER BY t.tx_date DESC;
        """, (chosen_partner_id,))

        if not df_partner_tx.empty:
            st.dataframe(df_partner_tx.fillna("-"), use_container_width=True, hide_index=True)
        else:
            st.info(f"لا توجد حركات مسحوبات مسجلة للشريك {partner_choice}.")
