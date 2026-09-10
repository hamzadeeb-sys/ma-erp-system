import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, time
import os
import base64
import io
import re

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 1. إعدادات الصفحة الأساسية
logo_filename = "MA Logo.png" if os.path.exists("MA Logo.png") else ("Mosab/MA Logo.png" if os.path.exists("Mosab/MA Logo.png") else None)

st.set_page_config(
    page_title="MA Real Estate | منظومة الإدارة والرقابة المالية",
    page_icon=logo_filename if logo_filename else "🏛️",
    layout="wide"
)

# 2. بيانات الاتصال بقاعدة البيانات السحابية Supabase
DB_HOST = "aws-1-eu-west-1.pooler.supabase.com"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres.rufqwqbpuvbljtofjzmf"
DB_PASS = "J+xqbELb/47pxxu"

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

def get_base64_image(image_path):
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

logo_b64 = get_base64_image(logo_filename)

def to_excel_download_link(df, filename):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='التقرير المالي')
    return output.getvalue()

def get_next_invoice_id(conn):
    cur = conn.cursor()
    cur.execute("SELECT id FROM transactions WHERE id ~ '^PAY-[0-9]+' ORDER BY id DESC LIMIT 50;")
    rows = cur.fetchall()
    cur.close()
    max_num = 0
    if rows:
        for r in rows:
            match = re.search(r'^PAY-(\d+)', str(r[0]))
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
    if max_num > 0:
        return f"PAY-{(max_num + 1):05d}"
    else:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM transactions;")
        cnt = cur.fetchone()[0]
        cur.close()
        return f"PAY-{(cnt + 1):05d}"

def generate_receipt_pdf(tx_data, items_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('MainTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=18, leading=22, alignment=1, textColor=colors.HexColor('#0F4733'))
    sub_title_style = ParagraphStyle('SubTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=11, leading=14, alignment=1, textColor=colors.HexColor('#BE9D5F'))
    normal_style = ParagraphStyle('NormalText', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=14, textColor=colors.HexColor('#44494B'))

    story.append(Paragraph("MA REAL ESTATE DEVELOPMENT &amp; CONTRACTING", title_style))
    story.append(Paragraph("Financial Receipt &amp; Voucher - Sanad Rasmi", sub_title_style))
    story.append(Spacer(1, 15))

    header_data = [
        [f"Voucher No: {tx_data['id']}", f"Date: {tx_data['tx_date']}"],
        [f"Project: {tx_data['project_name']}", f"Party: {tx_data['stakeholder_name']}"],
        [f"Amount: {tx_data['amount']:,.2f} {tx_data['currency']}", f"Method: {tx_data['payment_method']}"],
        [f"Equivalent: ${tx_data['amount_usd']:,.2f} USD", f"Type: {tx_data['tx_type']}"]
    ]
    t_header = Table(header_data, colWidths=[260, 260])
    t_header.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F9F9F8')),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#0F4733')),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#BE9D5F'))
    ]))
    story.append(t_header)
    story.append(Spacer(1, 15))

    if items_data:
        story.append(Paragraph("Detailed Items / Bayan:", normal_style))
        story.append(Spacer(1, 6))
        item_table_data = [["Item / Description", "Category", "Qty", "Unit Price", "Total"]]
        for it in items_data:
            item_table_data.append([str(it[0]), str(it[1]), f"{float(it[2]):,.2f}", f"{float(it[3]):,.2f}", f"{float(it[4]):,.2f}"])
        
        t_items = Table(item_table_data, colWidths=[180, 100, 70, 85, 85])
        t_items.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F4733')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('ALIGN', (2,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E1DE')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t_items)
        story.append(Spacer(1, 15))

    story.append(Paragraph(f"Notes / Description: {tx_data.get('description', '')}", normal_style))
    story.append(Spacer(1, 35))

    sig_data = [["Accountant Signature:", "Management Approval:", "Receiver Signature:"]]
    t_sig = Table(sig_data, colWidths=[175, 175, 175])
    t_sig.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#0F4733')),
        ('TOPPADDING', (0,0), (-1,-1), 20),
        ('LINEABOVE', (0,0), (-1,-1), 1, colors.HexColor('#BE9D5F'))
    ]))
    story.append(t_sig)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def generate_investor_statement_pdf(investor_name, proj_name, stats, tx_rows):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
    story = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('InvTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=18, leading=22, alignment=1, textColor=colors.HexColor('#0F4733'))
    sub_title_style = ParagraphStyle('InvSubTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=11, leading=14, alignment=1, textColor=colors.HexColor('#BE9D5F'))
    norm_bold = ParagraphStyle('NB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=12)

    story.append(Paragraph("MA REAL ESTATE DEVELOPMENT &amp; CONTRACTING", title_style))
    story.append(Paragraph(f"Official Statement of Account - {investor_name}", sub_title_style))
    story.append(Spacer(1, 15))

    summary_data = [
        [f"Investor: {investor_name}", f"Project: {proj_name}"],
        [f"Total Paid: ${stats['paid']:,.2f} USD", f"Execution Costs: ${stats['costs']:,.2f} USD"],
        [f"Management Fee ({stats['fee_rate']}%): ${stats['fees']:,.2f} USD", f"Net Outstanding Balance: ${stats['balance']:,.2f} USD"]
    ]
    t_sum = Table(summary_data, colWidths=[270, 270])
    t_sum.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F9F9F8')),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#0F4733')),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#BE9D5F')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_sum)
    story.append(Spacer(1, 15))

    story.append(Paragraph("Account Transactions History:", norm_bold))
    story.append(Spacer(1, 6))

    tx_table_data = [["Tx ID", "Date", "Type", "Direction", "Amount", "Curr", "USD Equiv", "Method"]]
    for r in tx_rows:
        tx_table_data.append([str(r[0]), str(r[1]), str(r[2]), str(r[3]), f"{float(r[4]):,.2f}", str(r[5]), f"${float(r[6]):,.2f}", str(r[7])])

    t_tx = Table(tx_table_data, colWidths=[65, 60, 100, 50, 75, 45, 75, 70])
    t_tx.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F4733')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E1DE')),
        ('ALIGN', (3,0), (6,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_tx)
    story.append(Spacer(1, 25))

    sig_data = [["Managing Partner Approval:", "Investor Confirmation:"]]
    t_sig = Table(sig_data, colWidths=[270, 270])
    t_sig.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#0F4733')),
        ('TOPPADDING', (0,0), (-1,-1), 20),
        ('LINEABOVE', (0,0), (-1,-1), 1, colors.HexColor('#BE9D5F'))
    ]))
    story.append(t_sig)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# 3. الهوية البصرية
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');
    * { font-family: 'Cairo', sans-serif !important; }
    [data-testid="stIconMaterial"], .material-symbols-rounded, button[data-testid="stSidebarCollapseButton"] *, button[data-testid="collapsedControl"] * { font-family: 'Material Symbols Rounded' !important; }
    .block-container { direction: rtl !important; text-align: right !important; padding-top: 5rem !important; padding-bottom: 3rem !important; }
    header[data-testid="stHeader"] { background: transparent !important; }
    .stApp { background-color: #F9F9F8 !important; }
    .stDeployButton, footer, #MainMenu { display: none !important; }
    section[data-testid="stSidebar"] { background-color: #0F4733 !important; border: none !important; direction: rtl !important; text-align: right !important; }
    section[data-testid="stSidebar"][aria-expanded="true"] { border-left: 2px solid #BE9D5F !important; }
    section[data-testid="stSidebar"][aria-expanded="false"] { border: none !important; }
    section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
    .metric-card { background: #FFFFFF; border-radius: 12px; padding: 18px 20px; border: 1px solid #E2E1DE; border-right: 6px solid #0F4733; box-shadow: 0 4px 15px rgba(15, 71, 51, 0.05); margin-bottom: 18px; direction: rtl; text-align: right; }
    .metric-title { color: #A29F98; font-size: 0.95rem; font-weight: 700; margin-bottom: 6px; }
    .metric-value-usd { color: #0F4733; font-size: 2rem; font-weight: 900; }
    .metric-value-gold { color: #BE9D5F; font-size: 2rem; font-weight: 900; }
    input, textarea, select, div[data-baseweb="select"] > div { background-color: #FFFFFF !important; color: #44494B !important; border: 1.5px solid #A29F98 !important; border-radius: 8px !important; font-weight: 600 !important; direction: rtl !important; text-align: right !important; }
    .stButton > button, .stDownloadButton > button { background-color: #0F4733 !important; color: #FFFFFF !important; border: 1.5px solid #BE9D5F !important; border-radius: 8px !important; padding: 8px 24px !important; font-weight: 800 !important; box-shadow: 0 4px 12px rgba(15, 71, 51, 0.15); }
    .stButton > button:hover, .stDownloadButton > button:hover { background-color: #BE9D5F !important; color: #0F4733 !important; border-color: #0F4733 !important; }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# تسجيل الدخول وتهيئة قاعدة البيانات
# ----------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_info = None

def login_user(username, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            full_name VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL,
            stakeholder_id INT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS office_appointments (
            id SERIAL PRIMARY KEY,
            visitor_name VARCHAR(255) NOT NULL,
            visitor_phone VARCHAR(100),
            visit_type VARCHAR(50) NOT NULL,
            visit_date DATE NOT NULL,
            visit_time TIME,
            host_person VARCHAR(255),
            purpose VARCHAR(255),
            status VARCHAR(50) DEFAULT 'مكتملة',
            notes TEXT,
            recorded_by VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        INSERT INTO app_users (username, password, full_name, role)
        VALUES 
            ('hamza', 'hamza123', 'حمزة ديب', 'Admin'),
            ('mosab', 'mosab123', 'مصعب المصري', 'Admin'),
            ('samer', 'samer123', 'سامر ديب', 'Partner'),
            ('manager', 'admin123', 'المدير العام', 'Manager'),
            ('accountant', 'acc123', 'محاسب الشركة', 'Accountant'),
            ('secretary', 'sec123', 'سكرتارية الاستقبال', 'Secretary')
        ON CONFLICT (username) DO NOTHING;
    """)
    conn.commit()
    cur.execute("SELECT id, username, full_name, role, stakeholder_id, is_active FROM app_users WHERE username = %s AND password = %s;", (username.strip(), password.strip()))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

if not st.session_state.authenticated:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c_log1, c_log2, c_log3 = st.columns([1, 1.5, 1])
    with c_log2:
        if logo_b64:
            st.markdown(f'<div style="text-align: center; margin-bottom: 15px;"><img src="data:image/png;base64,{logo_b64}" style="width: 140px;"></div>', unsafe_allow_html=True)
        st.markdown("""
            <div style="text-align: center; margin-bottom: 25px;">
                <h2 style="color: #0F4733; margin: 0;">منظومة الإدارة والرقابة المالية</h2>
                <div style="color: #BE9D5F; font-weight: 700;">MA Real Estate Development & Contracting</div>
            </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            st.markdown("##### 🔐 تسجيل الدخول إلى المنظومة")
            user_input = st.text_input("اسم المستخدم")
            pass_input = st.text_input("كلمة المرور", type="password")
            submitted = st.form_submit_button("تسجيل الدخول")
            if submitted:
                if user_input and pass_input:
                    user_data = login_user(user_input, pass_input)
                    if user_data:
                        if not user_data[5]:
                            st.error("⚠️ هذا الحساب مجمد حالياً، يرجى مراجعة إدارة النظام.")
                        else:
                            st.session_state.authenticated = True
                            st.session_state.user_info = {
                                "id": user_data[0],
                                "username": user_data[1],
                                "full_name": user_data[2],
                                "role": user_data[3],
                                "stakeholder_id": user_data[4]
                            }
                            st.success(f"مرحباً بك: {user_data[2]}")
                            st.rerun()
                    else:
                        st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")
                else:
                    st.warning("يرجى إدخال اسم المستخدم وكلمة المرور.")
    st.stop()

# ----------------------------------------------------
# الصلاحيات وتوزيع الشاشات
# ----------------------------------------------------
current_user = st.session_state.user_info
user_role = current_user['role']

if user_role == "Admin":
    allowed_menus = [
        "📊 لوحة المؤشرات العامة والأرصدة",
        "🤝 هيكل الشركاء ورأس المال والأرباح",
        "📑 كشوفات حسابات المستثمرين",
        "💱 التحويل بين الخزائن والصرافة",
        "🖨️ طباعة السندات وتصدير التقارير",
        "💳 مسيرات الرواتب الشهرية",
        "⏱️ جدول دوامات وساعات العمل",
        "📅 سجل المواعيد والزيارات",
        "📦 إدارة المخزون ومواد المشاريع",
        "👥 دليل وتعديل بيانات الأطراف",
        "📑 دفتر الحركات وسجل الفواتير",
        "➕ إضافة فاتورة وحركة متعددة البنود",
        "✏️ تعديل / إلغاء حركة مالية",
        "🏢 حسابات المشاريع والمستثمرين",
        "⚙️ الإدارة والتشغيل والتعاقدات"
    ]
elif user_role == "Manager":
    allowed_menus = [
        "📊 لوحة المؤشرات العامة والأرصدة",
        "🤝 هيكل الشركاء ورأس المال والأرباح",
        "📑 كشوفات حسابات المستثمرين",
        "🖨️ طباعة السندات وتصدير التقارير",
        "💳 مسيرات الرواتب الشهرية",
        "⏱️ جدول دوامات وساعات العمل",
        "📅 سجل المواعيد والزيارات",
        "📦 إدارة المخزون ومواد المشاريع",
        "👥 دليل وتعديل بيانات الأطراف",
        "📑 دفتر الحركات وسجل الفواتير",
        "🏢 حسابات المشاريع والمستثمرين"
    ]
elif user_role == "Accountant":
    allowed_menus = [
        "📊 لوحة المؤشرات العامة والأرصدة",
        "📑 كشوفات حسابات المستثمرين",
        "💱 التحويل بين الخزائن والصرافة",
        "🖨️ طباعة السندات وتصدير التقارير",
        "💳 مسيرات الرواتب الشهرية",
        "⏱️ جدول دوامات وساعات العمل",
        "📦 إدارة المخزون ومواد المشاريع",
        "👥 دليل وتعديل بيانات الأطراف",
        "📑 دفتر الحركات وسجل الفواتير",
        "➕ إضافة فاتورة وحركة متعددة البنود",
        "✏️ تعديل / إلغاء حركة مالية",
        "🏢 حسابات المشاريع والمستثمرين"
    ]
elif user_role == "Partner":
    allowed_menus = [
        "📊 لوحة المؤشرات العامة والأرصدة",
        "🤝 هيكل الشركاء ورأس المال والأرباح",
        "🏢 حسابات المشاريع والمستثمرين",
        "🖨️ طباعة السندات وتصدير التقارير"
    ]
elif user_role == "Secretary":
    allowed_menus = [
        "📅 سجل المواعيد والزيارات",
        "⏱️ جدول دوامات وساعات العمل"
    ]
elif user_role == "Employee":
    allowed_menus = [
        "👤 كشف حسابي ودوامي الذاتي"
    ]

# بناء القائمة الجانبية
with st.sidebar:
    if logo_b64:
        st.markdown(f'<div style="text-align: center; margin-bottom: 8px;"><img src="data:image/png;base64,{logo_b64}" style="width: 110px;"></div>', unsafe_allow_html=True)
    st.markdown("""
        <div style="text-align: center; color: #BE9D5F; font-size: 1.2rem; font-weight: 800; letter-spacing: 1px;">MA CO.</div>
        <div style="text-align: center; color: #A29F98; font-size: 0.8rem; margin-bottom: 12px;">للتطوير العقاري والإكساء</div>
    """, unsafe_allow_html=True)
    
    role_arabic = {
        "Admin": "مسؤول النظام العام (Admin)",
        "Manager": "المدير العام (قراءة واطلاع)",
        "Accountant": "محاسب الشركة المعتمد",
        "Partner": "شريك ومساهم (Partner)",
        "Secretary": "سكرتارية والاستقبال",
        "Employee": "موظف"
    }.get(user_role, user_role)

    st.markdown(f"""
        <div style="padding: 8px; background: rgba(190, 157, 95, 0.15); border-radius: 8px; text-align: center; margin-bottom: 15px;">
            <div style="font-size: 0.8rem; color: #BE9D5F;">المستخدم الحالي:</div>
            <div style="font-weight: 800; font-size: 1rem; color: #FFFFFF;">{current_user['full_name']}</div>
            <div style="font-size: 0.75rem; color: #E2E1DE;">الصلاحية: {role_arabic}</div>
        </div>
        <div style="height: 1px; background: #BE9D5F; margin-bottom: 12px;"></div>
    """, unsafe_allow_html=True)
    
    menu = st.sidebar.radio("التنقل السريع", allowed_menus)

    st.markdown("<br><hr style='border-color: rgba(190, 157, 95, 0.3);'>", unsafe_allow_html=True)
    if st.sidebar.button("🚪 تسجيل الخروج من النظام"):
        st.session_state.authenticated = False
        st.session_state.user_info = None
        st.rerun()

# ترويسة الصفحة الرسمية
col_title, col_logo = st.columns([5, 1])
with col_title:
    st.markdown("""
        <div style="direction: rtl; text-align: right; padding-top: 5px;">
            <h2 style="margin: 0; padding: 0; font-size: 1.7rem; color: #0F4733; font-weight: 800;">منظومة الإدارة والرقابة المالية</h2>
            <div style="color: #BE9D5F; font-size: 0.9rem; font-weight: 700; margin-top: 3px;">MA Real Estate Development &amp; Contracting</div>
        </div>
    """, unsafe_allow_html=True)
with col_logo:
    if logo_b64:
        st.markdown(f'<div style="text-align: left; padding-top: 5px;"><img src="data:image/png;base64,{logo_b64}" style="height: 48px;"></div>', unsafe_allow_html=True)

st.markdown("<hr style='border: 1px solid #BE9D5F; margin-top: 12px; margin-bottom: 25px;'>", unsafe_allow_html=True)

conn = get_connection()

# ====================================================
# 1. لوحة المؤشرات العامة والأرصدة
# ====================================================
if menu == "📊 لوحة المؤشرات العامة والأرصدة":
    st.subheader("💵 حالة الصناديق والسيولة اللحظية")
    query_vaults = """
        SELECT v.name AS vault_name, v.currency,
               COALESCE(SUM(CASE WHEN t.direction = 'IN' THEN t.amount ELSE -t.amount END), 0) AS current_balance
        FROM vaults v LEFT JOIN transactions t ON v.id = t.vault_id GROUP BY v.id, v.name, v.currency;
    """
    df_vaults = pd.read_sql(query_vaults, conn)
    col1, col2 = st.columns(2)
    with col1:
        usd_bal = df_vaults.loc[df_vaults['currency'] == 'USD', 'current_balance'].values[0] if not df_vaults.empty else 0
        st.markdown(f"""<div class="metric-card"><div class="metric-title">رصيد الخزينة بالدولار الأمريكي (USD)</div><div class="metric-value-usd">${usd_bal:,.2f}</div></div>""", unsafe_allow_html=True)
    with col2:
        syp_bal = df_vaults.loc[df_vaults['currency'] == 'SYP', 'current_balance'].values[0] if not df_vaults.empty else 0
        st.markdown(f"""<div class="metric-card" style="border-right-color: #BE9D5F;"><div class="metric-title">رصيد الخزينة بالليرة السورية (SYP)</div><div class="metric-value-gold">{syp_bal:,.0f} <span style="font-size: 1.1rem; color: #44494B;">ل.س</span></div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🏗️ مؤشرات أداء المشاريع النشطة")
    query_proj_summary = """
        SELECT p.name AS "المشروع", p.project_type AS "التصنيف", p.status AS "الحالة", COUNT(t.id) AS "عدد الحركات",
               COALESCE(SUM(CASE WHEN t.direction = 'OUT' THEN t.amount_usd ELSE 0 END), 0) AS "إجمالي المصروف ($)",
               COALESCE(SUM(CASE WHEN t.direction = 'IN' THEN t.amount_usd ELSE 0 END), 0) AS "إجمالي المقبوض ($)"
        FROM projects p LEFT JOIN transactions t ON p.id = t.project_id GROUP BY p.id, p.name, p.project_type, p.status;
    """
    df_proj_summary = pd.read_sql(query_proj_summary, conn)
    st.dataframe(df_proj_summary, use_container_width=True)

# ====================================================
# 2. هيكل الشركاء ورأس المال والأرباح
# ====================================================
elif menu == "🤝 هيكل الشركاء ورأس المال والأرباح":
    st.subheader("🤝 هيكل ملكية الشركة وحساب الحصص والأرباح")
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(SUM(ROUND(t.amount_usd * p.management_fee_rate, 2)), 0)
        FROM projects p JOIN transactions t ON p.id = t.project_id
        WHERE t.direction = 'OUT' AND p.project_type != 'Internal';
    """)
    total_company_profit = float(cur.fetchone()[0])

    cur.execute("SELECT partner_equity_pct, salary_amount, salary_currency FROM stakeholders WHERE name = 'حمزة ديب';")
    h_data = cur.fetchone()
    hamza_pct = float(h_data[0]) if (h_data and h_data[0] is not None and float(h_data[0]) > 0) else 15.00
    hamza_sal = float(h_data[1]) if h_data and h_data[1] is not None else 0.00
    hamza_sal_curr = h_data[2] if h_data and h_data[2] else 'USD'

    cur.execute("""
        SELECT COALESCE(SUM(amount_usd), 0) FROM transactions t
        LEFT JOIN stakeholders s ON t.stakeholder_id = s.id
        WHERE (s.name = 'مصعب المصري' OR t.description LIKE '%مصعب%')
          AND t.tx_type IN ('ايراد عام', 'مصروف عام') AND t.description LIKE '%راس مال%';
    """)
    mosab_capital = float(cur.fetchone()[0])
    if mosab_capital <= 0: mosab_capital = 11435.00

    cur.execute("""
        SELECT COALESCE(SUM(amount_usd), 0) FROM transactions t
        LEFT JOIN stakeholders s ON t.stakeholder_id = s.id
        WHERE (s.name = 'سامر ديب' OR t.description LIKE '%سامر%') AND t.tx_type = 'ايراد عام';
    """)
    samer_capital = float(cur.fetchone()[0])
    if samer_capital <= 0: samer_capital = 1814.00

    total_financial_capital = mosab_capital + samer_capital
    remaining_equity = max(0.0, 100.0 - hamza_pct)
    if total_financial_capital > 0:
        mosab_pct = (mosab_capital / total_financial_capital) * remaining_equity
        samer_pct = (samer_capital / total_financial_capital) * remaining_equity
    else:
        mosab_pct = remaining_equity
        samer_pct = 0.0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">إجمالي رأس المال التأسيسي المدفوع</div><div class="metric-value-usd">${total_financial_capital:,.2f}</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card" style="border-right-color: #BE9D5F;"><div class="metric-title">أرباح أتعاب الإدارة المتراكمة</div><div class="metric-value-gold">${total_company_profit:,.2f}</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card" style="border-right-color: #44494B;"><div class="metric-title">حصة حمزة ديب الإدارية المحمية</div><div class="metric-value-usd" style="color: #BE9D5F;">{hamza_pct:.2f}%</div></div>""", unsafe_allow_html=True)

    partners_breakdown = [
        {"الشريك": "مصعب المصري", "صفة الشراكة": "مؤسس وشريك مالي وإداري", "المساهمة برأس المال": f"${mosab_capital:,.2f}", "نسبة المساهمة المالية": f"{(mosab_capital/total_financial_capital*100):.1f}%", "نسبة الملكية من الشركة": f"{mosab_pct:.2f}%", "الأرباح المحققة ($)": f"${(total_company_profit * mosab_pct / 100.0):,.2f}"},
        {"الشريك": "سامر ديب", "صفة الشراكة": "مساهم برأس المال وشريك", "المساهمة برأس المال": f"${samer_capital:,.2f}", "نسبة المساهمة المالية": f"{(samer_capital/total_financial_capital*100):.1f}%", "نسبة الملكية من الشركة": f"{samer_pct:.2f}%", "الأرباح المحققة ($)": f"${(total_company_profit * samer_pct / 100.0):,.2f}"},
        {"الشريك": "حمزة ديب", "صفة الشراكة": "شريك إداري + موظف رسمي", "المساهمة برأس المال": "$0.00", "نسبة المساهمة المالية": "0.0%", "نسبة الملكية من الشركة": f"{hamza_pct:.2f}%", "الأرباح المحققة ($)": f"${(total_company_profit * hamza_pct / 100.0):,.2f}"}
    ]
    st.dataframe(pd.DataFrame(partners_breakdown), use_container_width=True)

    if user_role == "Admin":
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### ⚙️ تعديل نسبة وراتب حمزة ديب")
        with st.form("update_hamza_form"):
            col_h1, col_h2, col_h3 = st.columns(3)
            with col_h1:
                new_h_pct = st.number_input("نسبة حمزة ديب %", min_value=1.0, max_value=50.0, value=float(hamza_pct), step=1.0)
            with col_h2:
                new_h_sal = st.number_input("الراتب الشهري كموظف", min_value=0.0, value=float(hamza_sal), step=50.0)
            with col_h3:
                new_h_curr = st.selectbox("عملة الراتب", ["USD", "SYP"], index=0 if hamza_sal_curr == "USD" else 1)
            if st.form_submit_button("💾 تحديث النسبة فوراً"):
                cur.execute("UPDATE stakeholders SET partner_equity_pct = %s, salary_amount = %s, salary_currency = %s, role = 'Partner' WHERE name = 'حمزة ديب';", (new_h_pct, new_h_sal, new_h_curr))
                conn.commit()
                st.success("تم التحديث!")
                st.rerun()
    cur.close()

# ====================================================
# 3. سجل المواعيد والزيارات
# ====================================================
elif menu == "📅 سجل المواعيد والزيارات":
    st.subheader("📅 سجل تنظيم المواعيد وزيارات المكتب (مسبقة وفورية)")
    tab_v_list, tab_v_new = st.tabs(["📋 جدول الزيارات والمواعيد", "➕ تسجيل زيارة / موعد جديد"])

    with tab_v_list:
        cv1, cv2 = st.columns(2)
        with cv1: filter_v_type = st.selectbox("نوع الزيارة", ["الكل", "موعد مسبق", "زيارة فورية"])
        with cv2: filter_v_status = st.selectbox("الحالة", ["الكل", "قيد الانتظار", "جارية", "مكتملة", "ملغية"])

        query_appts = "SELECT id AS \"رقم القيد\", visitor_name AS \"الاسم\", visitor_phone AS \"الهاتف\", visit_type AS \"النوع\", visit_date AS \"التاريخ\", visit_time AS \"الوقت\", host_person AS \"الشخص المطلوب\", purpose AS \"الغاية\", status AS \"الحالة\", recorded_by AS \"المسجل\", notes AS \"ملاحظات\" FROM office_appointments WHERE 1=1"
        if filter_v_type != "الكل": query_appts += f" AND visit_type = '{filter_v_type}'"
        if filter_v_status != "الكل": query_appts += f" AND status = '{filter_v_status}'"
        query_appts += " ORDER BY visit_date DESC, visit_time DESC;"
        st.dataframe(pd.read_sql(query_appts, conn), use_container_width=True)

    with tab_v_new:
        if user_role in ["Admin", "Secretary"]:
            with st.form("new_visit_form", clear_on_submit=True):
                ca1, ca2 = st.columns(2)
                with ca1:
                    v_name = st.text_input("اسم الزائر / الضيف أو الجهة")
                    v_phone = st.text_input("رقم الهاتف")
                    v_type = st.selectbox("نوع الزيارة", ["زيارة فورية", "موعد مسبق"])
                    v_date = st.date_input("تاريخ الزيارة", datetime.now().date())
                with ca2:
                    v_time = st.time_input("وقت الزيارة", datetime.now().time())
                    v_host = st.selectbox("الشخص المطلوب مقابلته", ["المدير العام", "حمزة ديب", "مصعب المصري", "سامر ديب", "المحاسب", "آخر"])
                    v_purpose = st.text_input("الغاية من الزيارة")
                    v_status = st.selectbox("الحالة", ["قيد الانتظار", "جارية", "مكتملة", "ملغية"])
                v_notes = st.text_area("ملاحظات إضافية")

                if st.form_submit_button("💾 حفظ وتثبيت الزيارة"):
                    if v_name.strip():
                        cur = conn.cursor()
                        cur.execute("INSERT INTO office_appointments (visitor_name, visitor_phone, visit_type, visit_date, visit_time, host_person, purpose, status, notes, recorded_by) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);", (v_name.strip(), v_phone.strip(), v_type, v_date, v_time, v_host, v_purpose.strip(), v_status, v_notes.strip(), current_user['full_name']))
                        conn.commit()
                        cur.close()
                        st.success("تم تسجيل الزيارة بنجاح!")
                        st.rerun()

# ====================================================
# 4. جدول دوامات وساعات العمل
# ====================================================
elif menu == "⏱️ جدول دوامات وساعات العمل":
    st.subheader("⏱️ متابعة وتسجيل حضور ودوام الموظفين")
    emps_df = pd.read_sql("SELECT id, name FROM stakeholders WHERE role IN ('Employee', 'Partner') ORDER BY name;", conn)

    if user_role == "Secretary":
        st.markdown("### ➕ تسجيل حضور / انصراف يومي لموظف")
        with st.form("secretary_att_form", clear_on_submit=True):
            ca1, ca2 = st.columns(2)
            with ca1:
                selected_emp_att = st.selectbox("الموظف", emps_df['name'].tolist())
                att_date = st.date_input("تاريخ اليوم", datetime.now().date())
                att_status = st.selectbox("حالة الدوام", ["حاضر", "متأخر", "غياب", "إجازة"])
            with ca2:
                t_in = st.time_input("الدخول", time(9, 0))
                t_out = st.time_input("الانصراف", time(17, 0))
                att_notes = st.text_input("ملاحظات")
            if st.form_submit_button("💾 تثبيت قيد الدوام اليومي"):
                emp_id_val = int(emps_df.loc[emps_df['name'] == selected_emp_att, 'id'].values[0])
                cur = conn.cursor()
                duration = 8.0 if att_status in ["حاضر", "متأخر"] else 0.0
                cur.execute("INSERT INTO employee_attendance (employee_id, work_date, time_in, time_out, total_hours, status, notes) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (employee_id, work_date) DO UPDATE SET time_in = EXCLUDED.time_in, time_out = EXCLUDED.time_out, total_hours = EXCLUDED.total_hours, status = EXCLUDED.status, notes = EXCLUDED.notes;", (emp_id_val, att_date, t_in if att_status in ["حاضر", "متأخر"] else None, t_out if att_status in ["حاضر", "متأخر"] else None, duration, att_status, att_notes))
                conn.commit()
                cur.close()
                st.success(f"تم تسجيل دوام {selected_emp_att} بنجاح!")
    else:
        tab_att_log, tab_att_new, tab_att_rep = st.tabs(["📋 سجل الدوام الشهري", "➕ تسجيل حركة دوام", "📊 ملخص الساعات والغياب"])
        with tab_att_log:
            st.dataframe(pd.read_sql("SELECT a.id AS \"المعرف\", s.name AS \"الموظف\", a.work_date AS \"التاريخ\", a.time_in AS \"الحضور\", a.time_out AS \"الانصراف\", a.total_hours AS \"الساعات\", a.status AS \"الحالة\" FROM employee_attendance a JOIN stakeholders s ON a.employee_id = s.id ORDER BY a.work_date DESC;", conn), use_container_width=True)
        with tab_att_new:
            if user_role in ["Admin", "Accountant"]:
                with st.form("admin_att_form", clear_on_submit=True):
                    ca1, ca2 = st.columns(2)
                    with ca1:
                        selected_emp_att = st.selectbox("الموظف", emps_df['name'].tolist())
                        att_date = st.date_input("التاريخ", datetime.now().date())
                        att_status = st.selectbox("الحالة", ["حاضر", "متأخر", "غياب", "إجازة"])
                    with ca2:
                        t_in = st.time_input("الدخول", time(9, 0))
                        t_out = st.time_input("الانصراف", time(17, 0))
                        notes = st.text_input("ملاحظات")
                    if st.form_submit_button("💾 حفظ"):
                        emp_id_val = int(emps_df.loc[emps_df['name'] == selected_emp_att, 'id'].values[0])
                        cur = conn.cursor()
                        cur.execute("INSERT INTO employee_attendance (employee_id, work_date, time_in, time_out, total_hours, status, notes) VALUES (%s, %s, %s, %s, 8.0, %s, %s) ON CONFLICT (employee_id, work_date) DO UPDATE SET time_in = EXCLUDED.time_in, time_out = EXCLUDED.time_out, status = EXCLUDED.status, notes = EXCLUDED.notes;", (emp_id_val, att_date, t_in, t_out, att_status, notes))
                        conn.commit()
                        cur.close()
                        st.success("تم الحفظ!")
                        st.rerun()
        with tab_att_rep:
            st.dataframe(pd.read_sql("SELECT s.name AS \"الموظف\", COUNT(CASE WHEN a.status = 'حاضر' THEN 1 END) AS \"أيام الحضور\", COUNT(CASE WHEN a.status = 'غياب' THEN 1 END) AS \"أيام الغياب\", COALESCE(SUM(a.total_hours), 0) AS \"إجمالي الساعات\" FROM stakeholders s LEFT JOIN employee_attendance a ON s.id = a.employee_id WHERE s.role IN ('Employee', 'Partner') GROUP BY s.id, s.name;", conn), use_container_width=True)

# ====================================================
# 5. كشف حساب الموظف الذاتي
# ====================================================
elif menu == "👤 كشف حسابي ودوامي الذاتي":
    st.subheader(f"👤 كشف الدوام والراتب الشخصي: {current_user['full_name']}")
    emp_s_id = current_user.get("stakeholder_id")
    if not emp_s_id:
        st.info("لم يتم ربط هذا الحساب بملف موظف محدد.")
    else:
        st.markdown("#### ⏱️ سجل دوامك الشخصي")
        st.dataframe(pd.read_sql(f"SELECT work_date AS \"التاريخ\", time_in AS \"الحضور\", time_out AS \"الانصراف\", total_hours AS \"الساعات\", status AS \"الحالة\" FROM employee_attendance WHERE employee_id = {emp_s_id} ORDER BY work_date DESC;", conn), use_container_width=True)
        st.markdown("#### 💳 مسيرات الرواتب والمستحقات")
        st.dataframe(pd.read_sql(f"SELECT payroll_month AS \"الشهر\", base_salary AS \"الأساسي\", overtime_amount AS \"الإضافي\", deductions AS \"الخصومات\", net_salary AS \"صافي الراتب\", currency AS \"العملة\", payment_status AS \"الحالة\" FROM payroll_records WHERE employee_id = {emp_s_id} ORDER BY payroll_month DESC;", conn), use_container_width=True)

# ====================================================
# 6. كشوفات حسابات المستثمرين
# ====================================================
elif menu == "📑 كشوفات حسابات المستثمرين":
    st.subheader("📑 كشوفات حسابات المستثمرين والعملاء")
    all_projs = pd.read_sql("SELECT id, name, management_fee_rate FROM projects WHERE project_type != 'Internal' ORDER BY name;", conn)
    if not all_projs.empty:
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            selected_proj_name = st.selectbox("المشروع", all_projs['name'].tolist())
            proj_info = all_projs[all_projs['name'] == selected_proj_name].iloc[0]
            proj_id = int(proj_info['id'])
            fee_rate = float(proj_info['management_fee_rate'])
        with col_s2:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT s.name FROM transactions t JOIN stakeholders s ON t.stakeholder_id = s.id WHERE t.project_id = %s AND (t.tx_type LIKE %s OR s.role = 'Investor');", (proj_id, '%مقبوضات%'))
            linked_invs = [r[0] for r in cur.fetchall()]
            cur.close()
            investor_name = st.selectbox("المستثمر", linked_invs if linked_invs else ["العميل"])

        cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(amount_usd), 0) FROM transactions WHERE project_id = %s AND direction = 'IN';", (proj_id,))
        total_paid_in = float(cur.fetchone()[0])
        cur.execute("SELECT COALESCE(SUM(amount_usd), 0) FROM transactions WHERE project_id = %s AND direction = 'OUT';", (proj_id,))
        total_costs_out = float(cur.fetchone()[0])
        cur.close()

        mgmt_fee = total_costs_out * fee_rate
        net_balance = (total_costs_out + mgmt_fee) - total_paid_in

        c_inv1, c_inv2, c_inv3, c_inv4 = st.columns(4)
        with c_inv1: st.metric("المقبوضات", f"${total_paid_in:,.2f}")
        with c_inv2: st.metric("المصاريف والمواد", f"${total_costs_out:,.2f}")
        with c_inv3: st.metric(f"أتعاب الإدارة ({fee_rate*100:.0f}%)", f"${mgmt_fee:,.2f}")
        with c_inv4: st.metric("الصافي المستحق", f"${abs(net_balance):,.2f}")

        df_inv_tx = pd.read_sql(f"SELECT id AS \"رقم الفاتورة\", tx_date AS \"التاريخ\", tx_type AS \"نوع الحركة\", amount AS \"المبلغ\", currency AS \"العملة\", amount_usd AS \"المعادل $\", description AS \"البيان\" FROM transactions WHERE project_id = {proj_id} ORDER BY tx_date DESC;", conn)
        st.dataframe(df_inv_tx, use_container_width=True)

# ====================================================
# 7. التحويل والصرافة
# ====================================================
elif menu == "💱 التحويل بين الخزائن والصرافة":
    st.subheader("💱 التحويل المالي والصرافة بين الصناديق")
    df_v_bal = pd.read_sql("SELECT v.id, v.currency, COALESCE(SUM(CASE WHEN t.direction = 'IN' THEN t.amount ELSE -t.amount END), 0) AS balance FROM vaults v LEFT JOIN transactions t ON v.id = t.vault_id GROUP BY v.id, v.currency;", conn)
    usd_available = df_v_bal.loc[df_v_bal['currency'] == 'USD', 'balance'].values[0] if not df_v_bal.empty else 0.0
    syp_available = df_v_bal.loc[df_v_bal['currency'] == 'SYP', 'balance'].values[0] if not df_v_bal.empty else 0.0

    st.info(f"💵 المتاح بالدولار: **${usd_available:,.2f}** | 🪙 المتاح بالليرة: **{syp_available:,.0f} ل.س**")
    if user_role in ["Admin", "Accountant"]:
        with st.form("transfer_vault_form"):
            ct1, ct2, ct3 = st.columns(3)
            with ct1:
                tx_dir = st.selectbox("الاتجاه", ["من دولار إلى ليرة سورية", "من ليرة سورية إلى دولار"])
                t_date = st.date_input("التاريخ", datetime.now().date())
            with ct2:
                s_amt = st.number_input("المبلغ المحول", min_value=0.0, step=50.0)
                rate = st.number_input("سعر الصرف", min_value=1.0, value=131.0)
            with ct3:
                calc_res = s_amt * rate if "من دولار" in tx_dir else (s_amt / rate if rate > 0 else 0)
                st.markdown(f"**المبلغ المقابل:** {calc_res:,.2f}")
                notes = st.text_input("ملاحظات / الصراف", value="صرافة داخلية")
            if st.form_submit_button("🚀 اعتماد التحويل"):
                from_c = "USD" if "من دولار" in tx_dir else "SYP"
                to_c = "SYP" if "من دولار" in tx_dir else "USD"
                avail = usd_available if from_c == "USD" else syp_available
                if s_amt > 0 and s_amt <= avail:
                    cur = conn.cursor()
                    ts = int(datetime.now().timestamp())
                    v_src = 1 if from_c == "USD" else 2
                    v_dst = 2 if to_c == "SYP" else 1
                    amt_usd = s_amt if from_c == "USD" else calc_res
                    cur.execute("INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description) VALUES (%s, %s, 'تحويل بين الصناديق (صادر)', 1, 1, %s, %s, %s, %s, %s, 'OUT', 'صرافة', %s);", (f"TRF-O-{ts}", t_date, v_src, s_amt, from_c, rate, amt_usd, notes))
                    cur.execute("INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description) VALUES (%s, %s, 'تحويل بين الصناديق (وارد)', 1, 1, %s, %s, %s, %s, %s, 'IN', 'صرافة', %s);", (f"TRF-I-{ts}", t_date, v_dst, calc_res, to_c, rate, amt_usd, notes))
                    conn.commit()
                    cur.close()
                    st.success("تم ترحيل الصرافة!")
                    st.rerun()

# ====================================================
# 8. طباعة السندات وتصدير التقارير
# ====================================================
elif menu == "🖨️ طباعة السندات وتصدير التقارير":
    st.subheader("🖨️ طباعة السندات وتصدير التقارير")
    tab_pdf, tab_ex = st.tabs(["📄 طباعة سند مالي (PDF)", "📊 تصدير البيانات إلى Excel"])
    with tab_pdf:
        tx_options = pd.read_sql("SELECT t.id, t.amount, t.currency, s.name AS s_name FROM transactions t LEFT JOIN stakeholders s ON t.stakeholder_id = s.id ORDER BY t.tx_date DESC LIMIT 50;", conn)
        if not tx_options.empty:
            chosen_id = st.selectbox("اختر رقم السند", tx_options['id'].tolist())
            cur = conn.cursor()
            cur.execute("SELECT t.id, t.tx_date, t.tx_type, p.name, s.name, t.amount, t.currency, t.exchange_rate, t.amount_usd, t.payment_method, t.description FROM transactions t LEFT JOIN projects p ON t.project_id = p.id LEFT JOIN stakeholders s ON t.stakeholder_id = s.id WHERE t.id = %s;", (chosen_id,))
            tx_r = cur.fetchone()
            tx_dict = {'id': tx_r[0], 'tx_date': tx_r[1], 'tx_type': tx_r[2], 'project_name': tx_r[3], 'stakeholder_name': tx_r[4], 'amount': float(tx_r[5]), 'currency': tx_r[6], 'exchange_rate': float(tx_r[7]), 'amount_usd': float(tx_r[8]), 'payment_method': tx_r[9], 'description': tx_r[10] or ''}
            cur.execute("SELECT item_name, category, quantity, unit_price, total_price FROM invoice_items WHERE transaction_id = %s;", (chosen_id,))
            items_r = cur.fetchall()
            cur.close()
            pdf_bytes = generate_receipt_pdf(tx_dict, items_r)
            st.download_button("📥 تحميل السند PDF", data=pdf_bytes, file_name=f"Voucher_{chosen_id}.pdf", mime="application/pdf")
    with tab_ex:
        df_all_tx = pd.read_sql("SELECT * FROM transactions ORDER BY tx_date DESC;", conn)
        st.download_button("📥 تنزيل سجل الحركات Excel", data=to_excel_download_link(df_all_tx, "transactions.xlsx"), file_name="MA_Transactions.xlsx")

# ====================================================
# 9. مسيرات الرواتب الشهرية
# ====================================================
elif menu == "💳 مسيرات الرواتب الشهرية":
    st.subheader("💳 احتساب وصرف مسيرات الرواتب")
    emps_sal = pd.read_sql("SELECT id, name, salary_amount, salary_currency FROM stakeholders WHERE role IN ('Employee', 'Partner') AND salary_amount > 0;", conn)
    if not emps_sal.empty:
        c1, c2 = st.columns(2)
        with c1: selected_emp = st.selectbox("الموظف", emps_sal['name'].tolist())
        with c2: p_month = st.text_input("شهر المسير (YYYY-MM)", value=datetime.now().strftime("%Y-%m"))
        emp_row = emps_sal[emps_sal['name'] == selected_emp].iloc[0]
        base_s = float(emp_row['salary_amount'])
        curr_s = str(emp_row['salary_currency'])

        cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(overtime_hours), 0), COUNT(CASE WHEN status = 'غياب' THEN 1 END) FROM employee_attendance WHERE employee_id = %s AND TO_CHAR(work_date, 'YYYY-MM') = %s;", (int(emp_row['id']), p_month))
        att_d = cur.fetchone()
        cur.close()
        ot_h, abs_d = float(att_d[0]), int(att_d[1])
        ot_val = ot_h * (base_s / 240.0) * 1.5
        ded_val = abs_d * (base_s / 30.0)
        net_s = base_s + ot_val - ded_val

        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("الأساسي", f"{base_s:,.2f} {curr_s}")
        with col2: st.metric("إضافي", f"+{ot_val:,.2f}")
        with col3: st.metric("خصم غياب", f"-{ded_val:,.2f}")
        with col4: st.metric("صافي الراتب", f"{net_s:,.2f} {curr_s}")

        if user_role in ["Admin", "Accountant"]:
            if st.button("🚀 اعتماد وصرف الراتب وتحديث الخزينة"):
                cur = conn.cursor()
                sal_id = f"SAL-{p_month}-{int(emp_row['id'])}"
                v_id = 1 if curr_s == 'USD' else 2
                cur.execute("SELECT exchange_rate FROM transactions WHERE currency = 'SYP' ORDER BY tx_date DESC LIMIT 1;")
                s_rate = float(cur.fetchone()[0] or 131.0)
                amt_u = net_s if curr_s == 'USD' else (net_s / s_rate)
                cur.execute("INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description) VALUES (%s, CURRENT_DATE, 'راتب او سلفة', 1, %s, %s, %s, %s, %s, %s, 'OUT', 'كاش', %s);", (sal_id, int(emp_row['id']), v_id, net_s, curr_s, s_rate if curr_s == 'SYP' else 1.0, amt_u, f"صرف راتب شهر {p_month}"))
                cur.execute("INSERT INTO payroll_records (employee_id, payroll_month, base_salary, overtime_hours, overtime_amount, absence_days, deductions, net_salary, currency, payment_status, transaction_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'معتمد', %s);", (int(emp_row['id']), p_month, base_s, ot_h, ot_val, abs_d, ded_val, net_s, curr_s, sal_id))
                conn.commit()
                cur.close()
                st.success("تم صرف الراتب بنجاح!")
                st.rerun()

# ====================================================
# 10. المخزون ومواد المشاريع
# ====================================================
elif menu == "📦 إدارة المخزون ومواد المشاريع":
    st.subheader("📦 مستودع ومخزون مواد الشركة")
    tab_st, tab_iss = st.tabs(["🧱 جرد المواد", "📤 صرف مادة إلى مشروع"])
    with tab_st:
        st.dataframe(pd.read_sql("SELECT item_name AS \"المادة\", category AS \"التصنيف\", quantity_on_hand AS \"الكمية المتوفرة\", avg_unit_cost AS \"تكلفة الوحدة\", currency AS \"العملة\" FROM inventory_stock ORDER BY quantity_on_hand DESC;", conn), use_container_width=True)
    with tab_iss:
        if user_role in ["Admin", "Accountant"]:
            df_mats = pd.read_sql("SELECT item_name, quantity_on_hand, avg_unit_cost, currency FROM inventory_stock WHERE quantity_on_hand > 0;", conn)
            df_p = pd.read_sql("SELECT id, name FROM projects WHERE status = 'Active' AND project_type != 'Internal';", conn)
            if not df_mats.empty and not df_p.empty:
                with st.form("iss_mat_form"):
                    sel_mat = st.selectbox("المادة", df_mats['item_name'].tolist())
                    mat_inf = df_mats[df_mats['item_name'] == sel_mat].iloc[0]
                    sel_p = st.selectbox("المشروع", df_p['name'].tolist())
                    iss_q = st.number_input("الكمية", min_value=0.01, max_value=float(mat_inf['quantity_on_hand']), value=1.0)
                    if st.form_submit_button("🚀 اعتماد الصرف"):
                        p_id = int(df_p.loc[df_p['name'] == sel_p, 'id'].values[0])
                        tot = iss_q * float(mat_inf['avg_unit_cost'])
                        cur = conn.cursor()
                        cur.execute("UPDATE inventory_stock SET quantity_on_hand = quantity_on_hand - %s WHERE item_name = %s;", (iss_q, sel_mat))
                        cur.execute("INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description) VALUES (%s, CURRENT_DATE, 'صرف مواد من المخزون', %s, 1, 1, %s, %s, 1, %s, 'OUT', 'صرف مخزني', %s);", (f"MAT-{int(datetime.now().timestamp())}", p_id, tot, mat_inf['currency'], tot, f"صرف {iss_q} من {sel_mat}"))
                        conn.commit()
                        cur.close()
                        st.success("تم صرف المادة للمشروع بنجاح!")
                        st.rerun()

# ====================================================
# 11. دليل الأطراف (الجهات الخارجية)
# ====================================================
elif menu == "👥 دليل وتعديل بيانات الأطراف":
    st.subheader("👥 دليل كافة الأطراف والجهات الخارجية")
    tab_list, tab_add_ext = st.tabs(["📋 قائمة الأطراف المسجلة", "➕ إضافة جهة تعامل / طرف خارجي"])
    with tab_list:
        st.dataframe(pd.read_sql("SELECT id AS \"المعرف\", name AS \"الاسم\", role AS \"الدور\", phone AS \"الهاتف\", notes AS \"البيان\" FROM stakeholders ORDER BY id ASC;", conn), use_container_width=True)
    with tab_add_ext:
        if user_role in ["Admin", "Accountant"]:
            with st.form("ext_party_form", clear_on_submit=True):
                p_name = st.text_input("اسم الشخص / المعمل / المحامي / السائق")
                p_cat = st.selectbox("طبيعة التعامل", ["مورد مواد", "معمل تصنيع", "سائق / شحن", "محامي / قانوني", "مهندس استشاري", "ورشة تنفيذ", "أخرى"])
                p_phone = st.text_input("الهاتف")
                p_notes = st.text_area("ملاحظات التعامل")
                if st.form_submit_button("🚀 تسجيل الجهة الخارجية"):
                    if p_name.strip():
                        cur = conn.cursor()
                        cur.execute("INSERT INTO stakeholders (name, role, phone, salary_amount, salary_currency, partner_equity_pct, status, notes) VALUES (%s, 'General', %s, 0.0, 'USD', 0.0, 'نشط', %s) ON CONFLICT (name) DO UPDATE SET phone = EXCLUDED.phone, notes = EXCLUDED.notes;", (p_name.strip(), p_phone.strip(), f"[{p_cat}] {p_notes.strip()}"))
                        conn.commit()
                        cur.close()
                        st.success(f"تم تسجيل '{p_name}' بنجاح!")
                        st.rerun()

# ====================================================
# 12. دفتر الحركات وسجل الفواتير
# ====================================================
elif menu == "📑 دفتر الحركات وسجل الفواتير":
    st.subheader("سجل العمليات المالية والتدقيق")
    df_all_tx = pd.read_sql("SELECT t.id AS \"رقم الفاتورة\", t.tx_date AS \"التاريخ\", t.tx_type AS \"نوع الحركة\", p.name AS \"المشروع\", s.name AS \"الطرف\", t.amount AS \"المبلغ\", t.currency AS \"العملة\", t.amount_usd AS \"المعادل $\", t.direction AS \"الاتجاه\", t.description AS \"البيان\" FROM transactions t LEFT JOIN projects p ON t.project_id = p.id LEFT JOIN stakeholders s ON t.stakeholder_id = s.id ORDER BY t.tx_date DESC;", conn)
    st.dataframe(df_all_tx, use_container_width=True)

# ====================================================
# 13. إضافة حركة مالية وفاتورة
# ====================================================
elif menu == "➕ إضافة فاتورة وحركة متعددة البنود":
    if user_role in ["Admin", "Accountant"]:
        st.subheader("📄 تسجيل حركة مالية جديدة بفاتورة متعددة البنود")
        projs = pd.read_sql("SELECT id, name FROM projects ORDER BY name;", conn)
        parties = pd.read_sql("SELECT id, name FROM stakeholders ORDER BY name;", conn)
        auto_inv = get_next_invoice_id(conn)

        c1, c2, c3 = st.columns(3)
        with c1:
            inv_id = st.text_input("رقم الفاتورة (توليد تلقائي متسلسل)", value=auto_inv)
            t_date = st.date_input("التاريخ", datetime.now().date())
            t_type = st.selectbox("نوع الحركة", ["دفعة لمشروع", "شراء مواد وتخزين", "مقبوضات من مستثمر", "مصروف عام", "راتب او سلفة", "توزيع أرباح شريك", "ايراد عام"])
        with c2:
            p_name = st.selectbox("المشروع المرتبط", projs['name'].tolist())
            part_name = st.selectbox("الطرف / المورد / العميل", parties['name'].tolist())
            method = st.selectbox("طريقة الدفع", ["كاش", "حوالة", "شيك"])
        with c3:
            curr = st.selectbox("العملة", ["USD", "SYP"])
            rate = st.number_input("سعر الصرف", min_value=1.0, value=1.0 if curr == "USD" else 131.0)
            amount_f = st.number_input("المبلغ المالي الإجمالي", min_value=0.0, step=100.0)
        desc = st.text_area("البيان والملاحظات")

        if st.button("💾 حفظ وترحيل الفاتورة"):
            if amount_f > 0:
                p_id = int(projs.loc[projs['name'] == p_name, 'id'].values[0])
                s_id = int(parties.loc[parties['name'] == part_name, 'id'].values[0])
                v_id = 1 if curr == 'USD' else 2
                dir_m = 'IN' if ('مقبوضات' in t_type or 'ايراد' in t_type) else 'OUT'
                amt_u = amount_f if curr == 'USD' else (amount_f / rate)
                cur = conn.cursor()
                cur.execute("INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);", (inv_id, t_date, t_type, p_id, s_id, v_id, amount_f, curr, rate, amt_u, dir_m, method, desc))
                conn.commit()
                cur.close()
                st.success("تم ترحيل الفاتورة بنجاح!")
                st.rerun()

# ====================================================
# 14. تعديل / إلغاء حركة مالية
# ====================================================
elif menu == "✏️ تعديل / إلغاء حركة مالية":
    if user_role in ["Admin", "Accountant"]:
        st.subheader("✏️ تعديل أو حذف سند مالي")
        tx_l = pd.read_sql("SELECT id FROM transactions ORDER BY tx_date DESC LIMIT 50;", conn)['id'].tolist()
        s_tx = st.selectbox("اختر رقم السند", [""] + tx_l)
        if s_tx:
            cur = conn.cursor()
            cur.execute("SELECT amount, description FROM transactions WHERE id = %s;", (s_tx,))
            r_tx = cur.fetchone()
            cur.close()
            with st.form("edit_f"):
                n_amt = st.number_input("المبلغ", value=float(r_tx[0]))
                n_notes = st.text_area("البيان", value=r_tx[1] or "")
                if st.form_submit_button("💾 حفظ التعديل"):
                    cur = conn.cursor()
                    cur.execute("UPDATE transactions SET amount = %s, description = %s WHERE id = %s;", (n_amt, n_notes, s_tx))
                    conn.commit()
                    cur.close()
                    st.success("تم التعديل!")
                    st.rerun()
            if user_role == "Admin":
                if st.button("🗑️ حذف السند نهائياً"):
                    cur = conn.cursor()
                    cur.execute("DELETE FROM transactions WHERE id = %s;", (s_tx,))
                    conn.commit()
                    cur.close()
                    st.success("تم حذف السند!")
                    st.rerun()

# ====================================================
# 15. حسابات المشاريع والمستثمرين
# ====================================================
elif menu == "🏢 حسابات المشاريع والمستثمرين":
    st.subheader("كشف حسابات المشاريع وأرباح الإدارة")
    q_calc = """
        SELECT p.name AS "المشروع", p.status AS "الحالة", p.management_fee_rate * 100 AS "أتعاب الإدارة %",
               COALESCE(SUM(CASE WHEN t.direction = 'OUT' THEN t.amount_usd ELSE 0 END), 0) AS "تكاليف التنفيذ ($)",
               ROUND(COALESCE(SUM(CASE WHEN t.direction = 'OUT' THEN t.amount_usd ELSE 0 END), 0) * p.management_fee_rate, 2) AS "أتعاب الإدارة المستحقة ($)",
               COALESCE(SUM(CASE WHEN t.direction = 'IN' THEN t.amount_usd ELSE 0 END), 0) AS "المقبوض من المستثمر ($)"
        FROM projects p LEFT JOIN transactions t ON p.id = t.project_id WHERE p.project_type != 'Internal' GROUP BY p.id, p.name, p.status, p.management_fee_rate;
    """
    st.dataframe(pd.read_sql(q_calc, conn), use_container_width=True)

# ====================================================
# 16. الإدارة والتشغيل والتعاقدات (لوحة تحكم المستخدمين وكلمات السر الكاملة للأدمن)
# ====================================================
elif menu == "⚙️ الإدارة والتشغيل والتعاقدات":
    if user_role == "Admin":
        st.subheader("⚙️ لوحة تحكم الإدارة العليا (المستخدمين وكلمات المرور والصلاحيات)")

        tab_users_mgmt, tab_org_ops = st.tabs([
            "🔐 إدارة الحسابات وكلمات السر والصلاحيات",
            "🏗️ إدارة المشاريع والمستثمرين"
        ])

        with tab_users_mgmt:
            st.markdown("### 📋 سجل المستخدمين وكلمات السر الحالية")
            st.caption("كشف كامل بالحسابات وكلمات السر لإدارتها عند النسيان أو تعديل الصلاحيات:")
            
            query_users_full = """
                SELECT 
                    id AS "المعرف",
                    username AS "اسم الدخول",
                    password AS "كلمة المرور 🔑",
                    full_name AS "الاسم الكامل",
                    role AS "الصلاحية الممنوحة",
                    CASE WHEN is_active THEN 'نشط 🟢' ELSE 'مجمد 🛑' END AS "حالة الحساب",
                    created_at::date AS "تاريخ الإنشاء"
                FROM app_users
                ORDER BY id ASC;
            """
            df_users_full = pd.read_sql(query_users_full, conn)
            st.dataframe(df_users_full, use_container_width=True)

            st.markdown("---")
            col_u_edit, col_u_add = st.columns(2)

            with col_u_edit:
                st.markdown("#### ✏️ تعديل حساب / تغيير كلمة سر / تجميد / صلاحية")
                all_usernames = df_users_full["اسم الدخول"].tolist()
                sel_user = st.selectbox("اختر الحساب المطلوب تعديله:", all_usernames)

                if sel_user:
                    cur = conn.cursor()
                    cur.execute("SELECT id, username, password, full_name, role, is_active FROM app_users WHERE username = %s;", (sel_user,))
                    u_rec = cur.fetchone()
                    cur.close()

                    u_id, u_usr, u_pwd, u_fn, u_rl, u_act = u_rec
                    roles_list = ["Admin", "Manager", "Accountant", "Secretary", "Partner", "Employee"]
                    rl_idx = roles_list.index(u_rl) if u_rl in roles_list else 0

                    with st.form("edit_user_credentials_form"):
                        new_u_fn = st.text_input("الاسم الكامل", value=u_fn)
                        new_u_pwd = st.text_input("كلمة المرور الجديدة", value=u_pwd)
                        new_u_rl = st.selectbox("تعديل الصلاحية", roles_list, index=rl_idx)
                        new_u_act = st.selectbox("حالة الحساب", ["نشط", "تجميد الحساب"], index=0 if u_act else 1)

                        save_user_changes = st.form_submit_button("💾 حفظ تعديلات الحساب فوراً")
                        if save_user_changes:
                            cur = conn.cursor()
                            is_active_val = True if new_u_act == "نشط" else False
                            cur.execute("""
                                UPDATE app_users
                                SET full_name = %s, password = %s, role = %s, is_active = %s
                                WHERE id = %s;
                            """, (new_u_fn.strip(), new_u_pwd.strip(), new_u_rl, is_active_val, u_id))
                            conn.commit()
                            cur.close()
                            st.success(f"تم تحديث بيانات الحساب '{sel_user}' بنجاح!")
                            st.rerun()

                    if sel_user not in ["hamza", "mosab"]:
                        if st.button(f"🗑️ حذف حساب {sel_user} نهائياً", key="del_user_btn"):
                            cur = conn.cursor()
                            cur.execute("DELETE FROM app_users WHERE id = %s;", (u_id,))
                            conn.commit()
                            cur.close()
                            st.success(f"تم حذف الحساب {sel_user} نهائياً.")
                            st.rerun()

            with col_u_add:
                st.markdown("#### ➕ إنشاء حساب جديد")
                with st.form("add_new_app_user_form", clear_on_submit=True):
                    add_usr = st.text_input("اسم الدخول الجديد (Username)")
                    add_pwd = st.text_input("كلمة المرور (Password)")
                    add_fn = st.text_input("الاسم الكامل للمستخدم")
                    add_rl = st.selectbox("تحديد الدور والصلاحية", ["Manager", "Accountant", "Secretary", "Partner", "Employee", "Admin"])
                    
                    if st.form_submit_button("🚀 تفعيل وإنشاء الحساب"):
                        if add_usr.strip() and add_pwd.strip():
                            cur = conn.cursor()
                            try:
                                cur.execute("""
                                    INSERT INTO app_users (username, password, full_name, role, is_active)
                                    VALUES (%s, %s, %s, %s, TRUE);
                                """, (add_usr.strip(), add_pwd.strip(), add_fn.strip(), add_rl))
                                conn.commit()
                                st.success(f"تم إنشاء حساب '{add_usr}' بنجاح!")
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"اسم المستخدم مستخدم مسبقاً أو حدث خطأ: {e}")
                            finally:
                                cur.close()
                        else:
                            st.error("يرجى ملء اسم الدخول وكلمة المرور.")

        with tab_org_ops:
            st.markdown("### 🏗️ إدارة المشاريع والمستثمرين")
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                st.markdown("#### ➕ إنشاء مشروع جديد")
                with st.form("add_proj_quick", clear_on_submit=True):
                    p_name_n = st.text_input("اسم المشروع")
                    p_type_n = st.selectbox("النوع", ["Finishing", "Development", "Internal"])
                    p_fee_n = st.number_input("أتعاب الإدارة %", min_value=0.0, value=15.0)
                    if st.form_submit_button("فتح المشروع"):
                        if p_name_n.strip():
                            cur = conn.cursor()
                            cur.execute("INSERT INTO projects (name, project_type, management_fee_rate, status) VALUES (%s, %s, %s, 'Active') ON CONFLICT (name) DO NOTHING;", (p_name_n.strip(), p_type_n, p_fee_n / 100.0))
                            conn.commit()
                            cur.close()
                            st.success("تم إنشاء المشروع!")
                            st.rerun()
            with c_p2:
                st.markdown("#### ➕ تسجيل مستثمر جديد")
                with st.form("add_inv_quick", clear_on_submit=True):
                    inv_n = st.text_input("اسم المستثمر")
                    inv_ph = st.text_input("رقم الهاتف")
                    if st.form_submit_button("تسجيل المستثمر"):
                        if inv_n.strip():
                            cur = conn.cursor()
                            cur.execute("INSERT INTO stakeholders (name, role, phone, status) VALUES (%s, 'Investor', %s, 'نشط') ON CONFLICT (name) DO UPDATE SET role = 'Investor', status = 'نشط';", (inv_n.strip(), inv_ph.strip()))
                            conn.commit()
                            cur.close()
                            st.success("تم تسجيل المستثمر!")
                            st.rerun()

conn.close()
