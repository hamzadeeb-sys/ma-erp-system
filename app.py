import streamlit as st
import os

from core.auth import authenticate_user
from modules.dashboard import render_dashboard
from modules.stone_factory import render_stone_factory
from modules.partners import render_partners
from modules.finance import (
    render_vault_transfers,
    render_vouchers_and_reports,
    render_transactions_ledger,
    render_add_invoice,
    render_edit_transactions,
    render_investor_statements,
    render_projects_overview
)
from modules.hr import (
    render_attendance,
    render_payroll,
    render_employee_portal
)
from modules.operations import (
    render_inventory,
    render_stakeholders,
    render_appointments
)
from modules.admin import render_admin

# ----------------------------------------------------
# 1. إعدادات الصفحة
# ----------------------------------------------------
logo_filename = "MA Logo.png" if os.path.exists("MA Logo.png") else None

st.set_page_config(
    page_title="شركة MA العقارية | منظومة الإدارة والرقابة المالية",
    page_icon=logo_filename if logo_filename else "🏛️",
    layout="wide"
)

# ----------------------------------------------------
# 2. الهوية البصرية وضبط استقرار Glide Data Grid و Outline Icons
# ----------------------------------------------------
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');
    
    html, body, [class*="css"] { 
        font-family: 'Cairo', sans-serif !important; 
    }
    
    /* اتجاه الواجهة العام RTL */
    .block-container, p, label, .stMarkdown, .stText, h1, h2, h3, h4, h5, h6 {
        direction: rtl !important;
        text-align: right !important;
    }
    
    /* محاذاة أيقونات Material المتجهة */
    span[data-testid="stIconMaterial"] {
        font-family: 'Material Symbols Outlined' !important;
        vertical-align: middle !important;
        font-size: 1.2rem !important;
    }

    /* عزل محرك Glide Data Grid والكانفاس لمنع تشوه الأعمدة */
    [data-testid="stDataFrame"], 
    [data-testid="stDataEditor"],
    [data-testid="stDataFrame"] *, 
    [data-testid="stDataEditor"] * {
        direction: ltr !important;
        text-align: left !important;
    }

    #MainMenu, footer, header[data-testid="stHeader"] {
        visibility: hidden !important;
    }
    
    .stApp { 
        background-color: #F9F9F8 !important; 
    }
    
    /* بطاقات المؤشرات بهوية Octicon/GitHub */
    .metric-card { 
        background: #FFFFFF; 
        border-radius: 6px; 
        padding: 16px 20px; 
        border: 1px solid #D0D7DE; 
        border-top: 4px solid #0F4733; 
        box-shadow: 0 1px 3px rgba(31, 35, 40, 0.04); 
        margin-bottom: 15px; 
        direction: rtl; 
        text-align: center !important; 
    }
    .metric-title { 
        color: #57606A; 
        font-size: 0.85rem; 
        font-weight: 600; 
        margin-bottom: 6px; 
        text-align: center !important; 
    }
    .metric-value-usd { 
        color: #0F4733; 
        font-size: 1.75rem; 
        font-weight: 800; 
        text-align: center !important; 
    }
    .metric-value-gold { 
        color: #BE9D5F; 
        font-size: 1.75rem; 
        font-weight: 800; 
        text-align: center !important; 
    }
    
    input, textarea, select, div[data-baseweb="select"] > div { 
        background-color: #FFFFFF !important; 
        border: 1px solid #D0D7DE !important; 
        border-radius: 6px !important; 
        direction: rtl !important; 
        text-align: right !important; 
    }

    /* أزرار على نمط أزرار الأدوات في GitHub */
    .stButton > button, .stDownloadButton > button { 
        background-color: #0F4733 !important; 
        color: #FFFFFF !important; 
        border: 1px solid #0F4733 !important; 
        border-radius: 6px !important; 
        padding: 5px 18px !important; 
        font-weight: 600 !important; 
        font-size: 0.9rem !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    }
    .stButton > button:hover, .stDownloadButton > button:hover { 
        background-color: #BE9D5F !important; 
        border-color: #BE9D5F !important;
        color: #0F4733 !important; 
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# 3. إدارة الجلسة والمصادقة
# ----------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_info = None

if not st.session_state.authenticated:
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, c_log, _ = st.columns([1, 1.5, 1])
    with c_log:
        st.markdown("""
            <div style="text-align: center; margin-bottom: 25px;">
                <h2 style="color: #0F4733; margin: 0; font-weight: 800;">منظومة الإدارة والرقابة المالية</h2>
                <div style="color: #BE9D5F; font-weight: 700; margin-top: 4px;">شركة MA للتطوير العقاري والمقاولات</div>
            </div>
        """, unsafe_allow_html=True)
        with st.form("login_form"):
            st.markdown("##### :material/lock: تسجيل الدخول إلى المنظومة")
            u_input = st.text_input("اسم المستخدم")
            p_input = st.text_input("كلمة المرور", type="password")
            if st.form_submit_button("تسجيل الدخول", icon=":material/login:"):
                if u_input and p_input:
                    user_data = authenticate_user(u_input, p_input)
                    if user_data:
                        if not user_data["is_active"]:
                            st.error("الحساب معطل حالياً، راجع إدارة النظام.")
                        else:
                            st.session_state.authenticated = True
                            st.session_state.user_info = user_data
                            st.rerun()
                    else:
                        st.error("اسم المستخدم أو كلمة المرور غير صحيحة.")
                else:
                    st.warning("يرجى إدخال بيانات تسجيل الدخول.")
    st.stop()

# ----------------------------------------------------
# 4. التحكم بالأدوار والصلاحيات
# ----------------------------------------------------
current_user = st.session_state.user_info
user_role = current_user['role']
factory_menu_title = "حسابات وخزنة معمل الحجر"

if user_role == "Admin":
    allowed_menus = [
        "لوحة المؤشرات العامة والأرصدة",
        factory_menu_title,
        "هيكل الشركاء ورأس المال والأرباح",
        "كشوفات حسابات المستثمرين",
        "التحويل بين الخزائن والصرافة",
        "طباعة السندات وتصدير التقارير",
        "مسيرات الرواتب الشهرية",
        "جدول دوامات وساعات العمل",
        "سجل المواعيد والزيارات",
        "إدارة المخزون ومواد المشاريع",
        "دليل وتعديل بيانات الأطراف",
        "دفتر الحركات وسجل الفواتير",
        "إضافة فاتورة وحركة متعددة البنود",
        "تعديل / إلغاء حركة مالية",
        "حسابات المشاريع والمستثمرين",
        "الإدارة والتشغيل والتعاقدات"
    ]
elif user_role == "Manager":
    allowed_menus = [
        "لوحة المؤشرات العامة والأرصدة",
        factory_menu_title,
        "هيكل الشركاء ورأس المال والأرباح",
        "كشوفات حسابات المستثمرين",
        "طباعة السندات وتصدير التقارير",
        "مسيرات الرواتب الشهرية",
        "جدول دوامات وساعات العمل",
        "سجل المواعيد والزيارات",
        "إدارة المخزون ومواد المشاريع",
        "دليل وتعديل بيانات الأطراف",
        "دفتر الحركات وسجل الفواتير",
        "حسابات المشاريع والمستثمرين"
    ]
elif user_role == "Accountant":
    allowed_menus = [
        "لوحة المؤشرات العامة والأرصدة",
        factory_menu_title,
        "كشوفات حسابات المستثمرين",
        "التحويل بين الخزائن والصرافة",
        "طباعة السندات وتصدير التقارير",
        "مسيرات الرواتب الشهرية",
        "جدول دوامات وساعات العمل",
        "إدارة المخزون ومواد المشاريع",
        "دليل وتعديل بيانات الأطراف",
        "دفتر الحركات وسجل الفواتير",
        "إضافة فاتورة وحركة متعددة البنود",
        "تعديل / إلغاء حركة مالية",
        "حسابات المشاريع والمستثمرين"
    ]
elif user_role == "Partner":
    allowed_menus = [
        "لوحة المؤشرات العامة والأرصدة",
        factory_menu_title,
        "هيكل الشركاء ورأس المال والأرباح",
        "حسابات المشاريع والمستثمرين",
        "طباعة السندات وتصدير التقارير"
    ]
elif user_role == "Secretary":
    allowed_menus = [
        "سجل المواعيد والزيارات",
        "جدول دوامات وساعات العمل"
    ]
else:
    allowed_menus = [
        "كشف حسابي ودوامي الذاتي"
    ]

ROLE_NAME_AR = {
    "Admin": "مدير النظام العام",
    "Manager": "المدير العام",
    "Accountant": "محاسب الشركة",
    "Partner": "شريك ومساهم",
    "Secretary": "استقبال وإدارة مكتبية",
    "Employee": "موظف"
}

st.markdown(f"""
    <div style="background-color: #0F4733; padding: 10px 18px; border-radius: 6px; border: 1px solid #BE9D5F; text-align: center; margin-bottom: 18px; color: white; font-size: 0.95rem;">
        <b>شركة MA للتطوير العقاري والمقاولات</b> | المستخدم: <u>{current_user['full_name']}</u> ({ROLE_NAME_AR.get(user_role, user_role)})
    </div>
""", unsafe_allow_html=True)

col_nav1, col_nav2, col_nav3 = st.columns([1, 3, 1])
with col_nav2:
    menu = st.selectbox("نظام التوجيه والعمليات:", allowed_menus)
with col_nav3:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("تسجيل الخروج", icon=":material/logout:"):
        st.session_state.authenticated = False
        st.session_state.user_info = None
        st.rerun()

st.markdown("<hr style='border: 0.5px solid #D0D7DE; margin-top: 10px; margin-bottom: 20px;'>", unsafe_allow_html=True)

# ----------------------------------------------------
# 5. التوجيه التنفيذي للموديولات
# ----------------------------------------------------
if menu == "لوحة المؤشرات العامة والأرصدة":
    render_dashboard()
elif menu == factory_menu_title:
    render_stone_factory()
elif menu == "هيكل الشركاء ورأس المال والأرباح":
    render_partners(current_user)
elif menu == "كشوفات حسابات المستثمرين":
    render_investor_statements()
elif menu == "التحويل بين الخزائن والصرافة":
    render_vault_transfers(current_user)
elif menu == "طباعة السندات وتصدير التقارير":
    render_vouchers_and_reports()
elif menu == "مسيرات الرواتب الشهرية":
    render_payroll(current_user)
elif menu == "جدول دوامات وساعات العمل":
    render_attendance(current_user)
elif menu == "سجل المواعيد والزيارات":
    render_appointments(current_user)
elif menu == "إدارة المخزون ومواد المشاريع":
    render_inventory(current_user)
elif menu == "دليل وتعديل بيانات الأطراف":
    render_stakeholders(current_user)
elif menu == "دفتر الحركات وسجل الفواتير":
    render_transactions_ledger()
elif menu == "إضافة فاتورة وحركة متعددة البنود":
    render_add_invoice(current_user)
elif menu == "تعديل / إلغاء حركة مالية":
    render_edit_transactions(current_user)
elif menu == "حسابات المشاريع والمستثمرين":
    render_projects_overview()
elif menu == "الإدارة والتشغيل والتعاقدات":
    render_admin()
elif menu == "كشف حسابي ودوامي الذاتي":
    render_employee_portal(current_user)
