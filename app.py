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
    initial_sidebar_state="collapsed"
)

# ----------------------------------------------------
# 2. الهوية البصرية وضبط استقرار الحاويات
# ----------------------------------------------------
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');
    
    html, body, [class*="css"] { 
        font-family: 'Cairo', sans-serif !important; 
    }
    
    /* ضبط اتجاه الواجهة العام RTL */
    .block-container, p, label, .stMarkdown, .stText, h1, h2, h3, h4, h5, h6 {
        direction: rtl !important;
        text-align: right !important;
    }
    
    /* ضبط محاذاة الأيقونات المتجهة */
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

    /* إخفاء السايدبار والهيدر الأصلي */
    [data-testid="stSidebar"], 
    [data-testid="collapsedControl"], 
    header[data-testid="stHeader"],
    #MainMenu, 
    footer, 
    .stAppDeployButton,
    [data-testid="stToolbar"],
    div[data-testid="stDecoration"] {
        display: none !important;
        visibility: hidden !important;
    }

    .stApp { 
        background-color: #F9F9F8 !important; 
    }

    /* تنسيق الحاويات المؤطرة لتطابق النمط المؤسسي النظيف */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border: 1px solid #D0D7DE !important;
        border-top: 4px solid #0F4733 !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 3px rgba(31, 35, 40, 0.05) !important;
        padding: 14px !important;
        margin-bottom: 12px !important;
        height: 100% !important;
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
        padding: 6px 18px !important; 
        font-weight: 600 !important; 
        font-size: 0.9rem !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        margin-top: 4px !important;
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
                            st.session_state.current_page = "HOME"
                            st.rerun()
                    else:
                        st.error("اسم المستخدم أو كلمة المرور غير صحيحة.")
                else:
                    st.warning("يرجى إدخال بيانات تسجيل الدخول.")
    st.stop()

# ----------------------------------------------------
# 4. كتالوج المنظومة والأدوار
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

# هيكلة القطاعات مع التوصيف لملء الحاويات وظيفياً
MODULE_CATALOG = [
    {
        "category": "لوحة القيادة والمؤشرات",
        "icon": ":material/dashboard:",
        "desc": "مراقبة السيولة النقدية، حركة الصناديق، وحسابات معمل الحجر المستقلة.",
        "items": [
            {"title": "لوحة المؤشرات العامة والأرصدة", "icon": ":material/analytics:"},
            {"title": factory_menu_title, "icon": ":material/precision_manufacturing:"},
        ]
    },
    {
        "category": "المشاريع والشركاء",
        "icon": ":material/domain:",
        "desc": "إدارة تكاليف المشاريع، أتعاب الإدارة، كشوفات المستثمرين، وهيكل رأس المال.",
        "items": [
            {"title": "حسابات المشاريع والمستثمرين", "icon": ":material/domain_verification:"},
            {"title": "كشوفات حسابات المستثمرين", "icon": ":material/manage_accounts:"},
            {"title": "هيكل الشركاء ورأس المال والأرباح", "icon": ":material/handshake:"},
        ]
    },
    {
        "category": "العمليات المالية والمحاسبة",
        "icon": ":material/account_balance:",
        "desc": "تسجيل الفواتير الذري، دفتر القيود العام، الصرافة الداخلية، وإصدار السندات.",
        "items": [
            {"title": "إضافة فاتورة وحركة متعددة البنود", "icon": ":material/post_add:"},
            {"title": "دفتر الحركات وسجل الفواتير", "icon": ":material/receipt_long:"},
            {"title": "التحويل بين الخزائن والصرافة", "icon": ":material/currency_exchange:"},
            {"title": "تعديل / إلغاء حركة مالية", "icon": ":material/edit_note:"},
            {"title": "طباعة السندات وتصدير التقارير", "icon": ":material/print:"},
        ]
    },
    {
        "category": "الموارد البشرية والمكتب",
        "icon": ":material/badge:",
        "desc": "تتبع سجلات الحضور والانصراف، احتساب مسيرات الرواتب، وسجل الزيارات.",
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
        "desc": "جرد وحركات المواد والمخزون، دليل الأطراف والموردين، وضبط المستخدمين.",
        "items": [
            {"title": "إدارة المخزون ومواد المشاريع", "icon": ":material/inventory_2:"},
            {"title": "دليل وتعديل بيانات الأطراف", "icon": ":material/group:"},
            {"title": "الإدارة والتشغيل والتعاقدات", "icon": ":material/admin_panel_settings:"},
        ]
    },
]

# تصفية القطاعات وفق الصلاحيات
user_categories = []
for cat in MODULE_CATALOG:
    valid_items = [it for it in cat["items"] if it["title"] in allowed_menus]
    if valid_items:
        user_categories.append({
            "category": cat["category"],
            "icon": cat["icon"],
            "desc": cat["desc"],
            "items": valid_items
        })

if "current_page" not in st.session_state:
    st.session_state.current_page = "HOME"

# ----------------------------------------------------
# 5. شريط المسار العلوي الموحد
# ----------------------------------------------------
col_b1, col_b2, col_b3 = st.columns([1.2, 2.8, 1])

with col_b1:
    if st.session_state.current_page != "HOME":
        if st.button("العودة للرئيسية", icon=":material/arrow_forward:", use_container_width=True):
            st.session_state.current_page = "HOME"
            st.rerun()
    else:
        st.markdown("""
            <div style="background: #0F4733; color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold; text-align: center; font-size: 0.9rem;">
                🏛️ شركة MA العقارية
            </div>
        """, unsafe_allow_html=True)

with col_b2:
    if st.session_state.current_page == "HOME":
        st.markdown("""
            <div style="background: #FFFFFF; padding: 6px 14px; border-radius: 6px; border: 1px solid #D0D7DE; font-size: 0.85rem; color: #57606A; line-height: 24px;">
                <b>الرئيسية</b> &nbsp;›&nbsp; <span>بوابة القطاعات والخدمات المركزية</span>
            </div>
        """, unsafe_allow_html=True)
    else:
        cat_title = "القطاع المالي"
        for c in user_categories:
            if any(it["title"] == st.session_state.current_page for it in c["items"]):
                cat_title = c["category"]
                break
        st.markdown(f"""
            <div style="background: #FFFFFF; padding: 6px 14px; border-radius: 6px; border: 1px solid #D0D7DE; font-size: 0.85rem; color: #57606A; line-height: 24px;">
                <span>الرئيسية</span> &nbsp;›&nbsp; 
                <span>{cat_title}</span> &nbsp;›&nbsp; 
                <b style="color: #0F4733;">{st.session_state.current_page}</b>
            </div>
        """, unsafe_allow_html=True)

with col_b3:
    col_u_name, col_u_out = st.columns([2, 1])
    with col_u_name:
        st.markdown(f"""
            <div style="background: #F6F8FA; padding: 6px; border-radius: 6px; border: 1px solid #D0D7DE; font-size: 0.75rem; text-align: center; color: #1F2328; font-weight: bold;">
                {current_user['full_name']}
            </div>
        """, unsafe_allow_html=True)
    with col_u_out:
        if st.button("", icon=":material/logout:", help="تسجيل الخروج", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_info = None
            st.session_state.current_page = "HOME"
            st.rerun()

st.markdown("<hr style='border: 0.5px solid #D0D7DE; margin-top: 10px; margin-bottom: 20px;'>", unsafe_allow_html=True)

# ----------------------------------------------------
# 6. شاشة البوابة المركزية بهندسة متوازنة (2 + 3 Grid)
# ----------------------------------------------------
def render_category_card(cat):
    with st.container(border=True):
        st.markdown(f"#### {cat['icon']} {cat['category']}")
        st.caption(cat["desc"])
        st.markdown("<hr style='margin: 8px 0; border: 0.5px solid #E1E4E8;'>", unsafe_allow_html=True)
        for it in cat["items"]:
            if st.button(it["title"], icon=it["icon"], use_container_width=True, key=f"portal_btn_{it['title']}"):
                st.session_state.current_page = it["title"]
                st.rerun()

if st.session_state.current_page == "HOME":
    st.markdown("### :material/grid_view: بوابة العمليات والقطاعات التنفيذية")
    st.caption("حدد القطاع أو الشاشة المطلوبة للبدء المباشر:")

    # إذا كانت القطاعات مكتملة (5 قطاعات): تطبيق المعمارية المتوازنة (2 في الأعلى + 3 في الأسفل)
    if len(user_categories) == 5:
        # الصف الأول: القطاعات الاستراتيجية (نصفين متطابقين 50% / 50%)
        row1_c1, row1_c2 = st.columns(2)
        with row1_c1:
            render_category_card(user_categories[0])
        with row1_c2:
            render_category_card(user_categories[1])

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        # الصف الثاني: القطاعات التشغيلية (3 أثلاث متطابقة 33% / 33% / 33%)
        row2_c1, row2_c2, row2_c3 = st.columns(3)
        with row2_c1:
            render_category_card(user_categories[2])
        with row2_c2:
            render_category_card(user_categories[3])
        with row2_c3:
            render_category_card(user_categories[4])

    else:
        # شبكة متجاوبة ديناميكية لأصحاب الصلاحيات المحدودة (مستخدمين عاديين / سكرتاريا)
        cols_count = min(len(user_categories), 3)
        dyn_cols = st.columns(cols_count)
        for idx, cat in enumerate(user_categories):
            with dyn_cols[idx % cols_count]:
                render_category_card(cat)

# ----------------------------------------------------
# 7. توجيه الشاشات التابعة
# ----------------------------------------------------
else:
    target = st.session_state.current_page

    if target == "لوحة المؤشرات العامة والأرصدة":
        render_dashboard()
    elif target == factory_menu_title:
        render_stone_factory()
    elif target == "هيكل الشركاء ورأس المال والأرباح":
        render_partners(current_user)
    elif target == "كشوفات حسابات المستثمرين":
        render_investor_statements()
    elif target == "التحويل بين الخزائن والصرافة":
        render_vault_transfers(current_user)
    elif target == "طباعة السندات وتصدير التقارير":
        render_vouchers_and_reports()
    elif target == "مسيرات الرواتب الشهرية":
        render_payroll(current_user)
    elif target == "جدول دوامات وساعات العمل":
        render_attendance(current_user)
    elif target == "سجل المواعيد والزيارات":
        render_appointments(current_user)
    elif target == "إدارة المخزون ومواد المشاريع":
        render_inventory(current_user)
    elif target == "دليل وتعديل بيانات الأطراف":
        render_stakeholders(current_user)
    elif target == "دفتر الحركات وسجل الفواتير":
        render_transactions_ledger()
    elif target == "إضافة فاتورة وحركة متعددة البنود":
        render_add_invoice(current_user)
    elif target == "تعديل / إلغاء حركة مالية":
        render_edit_transactions(current_user)
    elif target == "حسابات المشاريع والمستثمرين":
        render_projects_overview()
    elif target == "الإدارة والتشغيل والتعاقدات":
        render_admin()
    elif target == "كشف حسابي ودوامي الذاتي":
        render_employee_portal(current_user)
