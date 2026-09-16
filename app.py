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
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------------------------------------------
# 2. الهوية البصرية وتثبيت مقبض القائمة في منتصف الشاشة
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
    
    /* ضبط أيقونات Material المتجهة */
    span[data-testid="stIconMaterial"] {
        font-family: 'Material Symbols Outlined' !important;
        vertical-align: middle !important;
        font-size: 1.15rem !important;
    }

    /* عزل محرك Glide Data Grid لمنع تشوه الأعمدة */
    [data-testid="stDataFrame"], 
    [data-testid="stDataEditor"],
    [data-testid="stDataFrame"] *, 
    [data-testid="stDataEditor"] * {
        direction: ltr !important;
        text-align: left !important;
    }

    /* إخفاء عناصر المطور والفوتر */
    #MainMenu, 
    footer, 
    .stAppDeployButton,
    [data-testid="stToolbar"],
    div[data-testid="stDecoration"] {
        display: none !important;
        visibility: hidden !important;
    }

    /* تفريغ الهيدر لمنع حجب النقرات ومنع اقتطاع العناصر */
    header[data-testid="stHeader"] {
        background: transparent !important;
        pointer-events: none !important;
        height: 0px !important;
    }

    /* مقبض عائم لفتح الشريط الجانبي في منتصف ارتفاع الشاشة */
    [data-testid="stSidebarCollapsedControl"] {
        position: fixed !important;
        top: 50% !important;
        left: 0px !important;
        right: auto !important;
        transform: translateY(-50%) !important;
        display: flex !important;
        visibility: visible !important;
        align-items: center !important;
        justify-content: center !important;
        width: 34px !important;
        height: 52px !important;
        background-color: #0F4733 !important;
        border: 1.5px solid #BE9D5F !important;
        border-left: none !important;
        border-radius: 0 8px 8px 0 !important;
        box-shadow: 3px 0 12px rgba(15, 71, 51, 0.35) !important;
        z-index: 9999999 !important;
        pointer-events: auto !important;
        cursor: pointer !important;
        transition: all 0.2s ease-in-out !important;
    }

    [data-testid="stSidebarCollapsedControl"]:hover {
        width: 40px !important;
        background-color: #BE9D5F !important;
        border-color: #0F4733 !important;
    }

    [data-testid="stSidebarCollapsedControl"] svg,
    [data-testid="stSidebarCollapsedControl"] button {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
    }
    
    .stApp { 
        background-color: #F9F9F8 !important; 
    }
    
    /* تنسيق الشريط الجانبي */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #D0D7DE !important;
        border-left: none !important;
        padding-top: 1rem !important;
        direction: rtl !important;
    }
    section[data-testid="stSidebar"] * {
        direction: rtl !important;
        text-align: right !important;
    }

    /* بطاقات المؤشرات */
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
# 4. فهرس الشاشات والهيكل الهرمي للصلاحيات
# ----------------------------------------------------
current_user = st.session_state.user_info
user_role = current_user['role']
factory_menu_title = "حسابات وخزنة معمل الحجر"

ROLE_NAME_AR = {
    "Admin": "مدير النظام العام",
    "Manager": "المدير العام",
    "Accountant": "محاسب الشركة",
    "Partner": "شريك ومساهم",
    "Secretary": "استقبال وإدارة مكتبية",
    "Employee": "موظف"
}

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

MODULE_CATALOG = [
    {
        "category": "لوحة القيادة والمؤشرات",
        "icon": ":material/dashboard:",
        "items": [
            {"title": "لوحة المؤشرات العامة والأرصدة", "icon": ":material/analytics:"},
            {"title": factory_menu_title, "icon": ":material/precision_manufacturing:"},
        ]
    },
    {
        "category": "العمليات المالية والمحاسبة",
        "icon": ":material/account_balance:",
        "items": [
            {"title": "إضافة فاتورة وحركة متعددة البنود", "icon": ":material/post_add:"},
            {"title": "دفتر الحركات وسجل الفواتير", "icon": ":material/receipt_long:"},
            {"title": "التحويل بين الخزائن والصرافة", "icon": ":material/currency_exchange:"},
            {"title": "تعديل / إلغاء حركة مالية", "icon": ":material/edit_note:"},
            {"title": "طباعة السندات وتصدير التقارير", "icon": ":material/print:"},
        ]
    },
    {
        "category": "المشاريع والشركاء",
        "icon": ":material/domain:",
        "items": [
            {"title": "حسابات المشاريع والمستثمرين", "icon": ":material/domain_verification:"},
            {"title": "كشوفات حسابات المستثمرين", "icon": ":material/manage_accounts:"},
            {"title": "هيكل الشركاء ورأس المال والأرباح", "icon": ":material/handshake:"},
        ]
    },
    {
        "category": "الموارد البشرية والمكتب",
        "icon": ":material/badge:",
        "items": [
            {"title": "جدول دوامات وساعات العمل", "icon": ":material/schedule:"},
            {"title": "مسيرات الرواتب الشهرية", "icon": ":material/payments:"},
            {"title": "سجل المواعيد والزيارات", "icon": ":material/calendar_today:"},
            {"title": "كشف حسابي ودوامي الذاتي", "icon": ":material/account_circle:"},
        ]
    },
    {
        "category": "المستودع والإدارة العامة",
        "icon": ":material/settings:",
        "items": [
            {"title": "إدارة المخزون ومواد المشاريع", "icon": ":material/inventory_2:"},
            {"title": "دليل وتعديل بيانات الأطراف", "icon": ":material/group:"},
            {"title": "الإدارة والتشغيل والتعاقدات", "icon": ":material/admin_panel_settings:"},
        ]
    },
]

# تصفية الكتالوج وفق الصلاحيات
user_categories = []
for cat in MODULE_CATALOG:
    valid_items = [it for it in cat["items"] if it["title"] in allowed_menus]
    if valid_items:
        user_categories.append({
            "category": cat["category"],
            "icon": cat["icon"],
            "items": valid_items
        })

# تثبيت الشاشة المحددة في الـ Session State لضمان التزامن
if "active_screen" not in st.session_state or st.session_state.active_screen not in allowed_menus:
    st.session_state.active_screen = allowed_menus[0]

# تحديد القطاع النشط بناءً على الشاشة الحالية
active_cat = user_categories[0]
for cat in user_categories:
    if any(it["title"] == st.session_state.active_screen for it in cat["items"]):
        active_cat = cat
        break

# ----------------------------------------------------
# 5. الشريط الجانبي الهرمي
# ----------------------------------------------------
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; margin-bottom: 12px;">
            <h3 style="color: #0F4733; margin: 0; font-weight: 800; font-size: 1.25rem;">MA Real Estate</h3>
            <div style="color: #BE9D5F; font-size: 0.8rem; font-weight: 700;">منظومة الرقابة المالية</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
        <div style="background: #F6F8FA; border: 1px solid #D0D7DE; border-radius: 6px; padding: 10px; margin-bottom: 16px;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #1F2328;">{current_user['full_name']}</div>
            <div style="font-size: 0.75rem; color: #57606A; margin-top: 2px;">{ROLE_NAME_AR.get(user_role, user_role)}</div>
        </div>
    """, unsafe_allow_html=True)

    st.caption("القطاع الرئيسي")
    cat_names = [f"{c['icon']} {c['category']}" for c in user_categories]
    current_cat_idx = [i for i, c in enumerate(user_categories) if c['category'] == active_cat['category']]
    
    selected_cat_str = st.radio("اختر القطاع:", cat_names, index=current_cat_idx[0] if current_cat_idx else 0, label_visibility="collapsed", key="sidebar_cat_radio")
    selected_cat = next(c for c in user_categories if f"{c['icon']} {c['category']}" == selected_cat_str)

    st.markdown("<hr style='border: 0.5px solid #E1E4E8; margin: 12px 0;'>", unsafe_allow_html=True)

    st.caption("الشاشات والعمليات المتاحة")
    item_labels = [f"{it['icon']} {it['title']}" for it in selected_cat["items"]]
    
    current_item_idx = 0
    for idx, it in enumerate(selected_cat["items"]):
        if it["title"] == st.session_state.active_screen:
            current_item_idx = idx
            break

    selected_item_str = st.radio("اختر الشاشة:", item_labels, index=current_item_idx, label_visibility="collapsed", key=f"sidebar_item_radio_{selected_cat['category']}")
    new_screen = next(it["title"] for it in selected_cat["items"] if f"{it['icon']} {it['title']}" == selected_item_str)
    
    if new_screen != st.session_state.active_screen:
        st.session_state.active_screen = new_screen
        st.rerun()

    st.markdown("<hr style='border: 0.5px solid #E1E4E8; margin: 16px 0;'>", unsafe_allow_html=True)
    
    if st.button("تسجيل الخروج", icon=":material/logout:", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_info = None
        st.rerun()

# ----------------------------------------------------
# 6. شريط المسار + التنقل السريع الفوري (In-Page Navigation)
# ----------------------------------------------------
c_bread, c_quick = st.columns([2.5, 1.5])
with c_bread:
    st.markdown(f"""
        <div style="background: #FFFFFF; padding: 7px 14px; border-radius: 6px; border: 1px solid #D0D7DE; margin-bottom: 15px; font-size: 0.85rem; color: #57606A; line-height: 28px;">
            <span>الرئيسية</span> &nbsp;›&nbsp; 
            <span>{active_cat['category']}</span> &nbsp;›&nbsp; 
            <b style="color: #0F4733;">{st.session_state.active_screen}</b>
        </div>
    """, unsafe_allow_html=True)

with c_quick:
    # محول تنقل مباشر من قلب الصفحة يمنع الحصار عند انغلاق القائمة
    quick_choice = st.selectbox(
        "الانتقال السريع للشاشات:",
        allowed_menus,
        index=allowed_menus.index(st.session_state.active_screen),
        label_visibility="collapsed",
        key="in_page_quick_jump"
    )
    if quick_choice != st.session_state.active_screen:
        st.session_state.active_screen = quick_choice
        st.rerun()

# ----------------------------------------------------
# 7. توجيه الموديولات البرمجية
# ----------------------------------------------------
selected_screen_title = st.session_state.active_screen

if selected_screen_title == "لوحة المؤشرات العامة والأرصدة":
    render_dashboard()
elif selected_screen_title == factory_menu_title:
    render_stone_factory()
elif selected_screen_title == "هيكل الشركاء ورأس المال والأرباح":
    render_partners(current_user)
elif selected_screen_title == "كشوفات حسابات المستثمرين":
    render_investor_statements()
elif selected_screen_title == "التحويل بين الخزائن والصرافة":
    render_vault_transfers(current_user)
elif selected_screen_title == "طباعة السندات وتصدير التقارير":
    render_vouchers_and_reports()
elif selected_screen_title == "مسيرات الرواتب الشهرية":
    render_payroll(current_user)
elif selected_screen_title == "جدول دوامات وساعات العمل":
    render_attendance(current_user)
elif selected_screen_title == "سجل المواعيد والزيارات":
    render_appointments(current_user)
elif selected_screen_title == "إدارة المخزون ومواد المشاريع":
    render_inventory(current_user)
elif selected_screen_title == "دليل وتعديل بيانات الأطراف":
    render_stakeholders(current_user)
elif selected_screen_title == "دفتر الحركات وسجل الفواتير":
    render_transactions_ledger()
elif selected_screen_title == "إضافة فاتورة وحركة متعددة البنود":
    render_add_invoice(current_user)
elif selected_screen_title == "تعديل / إلغاء حركة مالية":
    render_edit_transactions(current_user)
elif selected_screen_title == "حسابات المشاريع والمستثمرين":
    render_projects_overview()
elif selected_screen_title == "الإدارة والتشغيل والتعاقدات":
    render_admin()
elif selected_screen_title == "كشف حسابي ودوامي الذاتي":
    render_employee_portal(current_user)
