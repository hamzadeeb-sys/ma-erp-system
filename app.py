import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, time
import os
import base64
import io

# مكتبات تصدير PDF
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

# 3. الهوية البصرية المعتمدة لشركة MA CO.
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');
    
    html, body, [class*="css"], .stMarkdown, p, span, label, h1, h2, h3, h4, h5, button, input, select, textarea {
        font-family: 'Cairo', sans-serif !important;
        direction: rtl !important;
        text-align: right !important;
    }

    .stApp {
        background-color: #F9F9F8 !important;
    }

    .stDeployButton, footer, #MainMenu {
        display: none !important;
    }

    button[data-testid="stSidebarCollapseButton"],
    button[data-testid="collapsedControl"] {
        color: #BE9D5F !important;
        background-color: #0F4733 !important;
        border: 1px solid #BE9D5F !important;
        border-radius: 8px !important;
        margin: 5px !important;
    }

    section[data-testid="stSidebar"] {
        background-color: #0F4733 !important;
        border-left: 2px solid #BE9D5F;
    }
    section[data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }

    input, textarea, select, div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        color: #44494B !important;
        border: 1.5px solid #A29F98 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    .metric-card {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 18px 20px;
        border: 1px solid #E2E1DE;
        border-right: 6px solid #0F4733;
        box-shadow: 0 4px 15px rgba(15, 71, 51, 0.05);
        margin-bottom: 18px;
        direction: rtl;
        text-align: right;
    }
    .metric-title {
        color: #A29F98;
        font-size: 0.95rem;
        font-weight: 700;
        margin-bottom: 6px;
    }
    .metric-value-usd {
        color: #0F4733;
        font-size: 2rem;
        font-weight: 900;
    }
    .metric-value-gold {
        color: #BE9D5F;
        font-size: 2rem;
        font-weight: 900;
    }

    .stButton > button, .stDownloadButton > button {
        background-color: #0F4733 !important;
        color: #FFFFFF !important;
        border: 1.5px solid #BE9D5F !important;
        border-radius: 8px !important;
        padding: 8px 24px !important;
        font-weight: 800 !important;
        box-shadow: 0 4px 12px rgba(15, 71, 51, 0.15);
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        background-color: #BE9D5F !important;
        color: #0F4733 !important;
        border-color: #0F4733 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# بوابة تسجيل الدخول والأمان
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
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO app_users (username, password, full_name, role)
        VALUES 
            ('hamza', 'hamza123', 'حمزة ديب', 'Admin'),
            ('mosab', 'mosab123', 'مصعب المصري', 'Admin'),
            ('samer', 'samer123', 'سامر ديب', 'Admin'),
            ('accountant', 'acc123', 'محاسب الشركة', 'Accountant')
        ON CONFLICT (username) DO NOTHING;
    """)
    conn.commit()
    cur.execute("SELECT id, username, full_name, role FROM app_users WHERE username = %s AND password = %s AND is_active = TRUE;", (username.strip(), password.strip()))
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
            st.markdown("##### 🔐 تسجيل الدخول إلى النظام")
            user_input = st.text_input("اسم المستخدم")
            pass_input = st.text_input("كلمة المرور", type="password")
            submitted = st.form_submit_button("تسجيل الدخول")
            if submitted:
                if user_input and pass_input:
                    user_data = login_user(user_input, pass_input)
                    if user_data:
                        st.session_state.authenticated = True
                        st.session_state.user_info = {
                            "id": user_data[0],
                            "username": user_data[1],
                            "full_name": user_data[2],
                            "role": user_data[3]
                        }
                        st.success(f"مرحباً بك أستاذ {user_data[2]}")
                        st.rerun()
                    else:
                        st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")
                else:
                    st.warning("يرجى إدخال اسم المستخدم وكلمة المرور.")
    st.stop()

# ----------------------------------------------------
# المستخدم الحالي وصلاحياته
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
        "📦 إدارة المخزون ومواد المشاريع",
        "👥 دليل وتعديل بيانات الأطراف",
        "📑 دفتر الحركات وسجل الفواتير",
        "➕ إضافة فاتورة وحركة متعددة البنود",
        "✏️ تعديل / إلغاء حركة مالية",
        "🏢 حسابات المشاريع والمستثمرين",
        "⚙️ الإدارة والتشغيل والتعاقدات"
    ]
else:
    allowed_menus = [
        "📊 لوحة المؤشرات العامة والأرصدة",
        "📑 كشوفات حسابات المستثمرين",
        "🖨️ طباعة السندات وتصدير التقارير",
        "⏱️ جدول دوامات وساعات العمل",
        "📦 إدارة المخزون ومواد المشاريع",
        "📑 دفتر الحركات وسجل الفواتير",
        "➕ إضافة فاتورة وحركة متعددة البنود",
        "🏢 حسابات المشاريع والمستثمرين"
    ]

# بناء القائمة الجانبية
with st.sidebar:
    if logo_b64:
        st.markdown(f'<div style="text-align: center; margin-bottom: 8px;"><img src="data:image/png;base64,{logo_b64}" style="width: 110px;"></div>', unsafe_allow_html=True)
    st.markdown("""
        <div style="text-align: center; color: #BE9D5F; font-size: 1.2rem; font-weight: 800; letter-spacing: 1px;">MA CO.</div>
        <div style="text-align: center; color: #A29F98; font-size: 0.8rem; margin-bottom: 12px;">للتطوير العقاري والإكساء</div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
        <div style="padding: 8px; background: rgba(190, 157, 95, 0.15); border-radius: 8px; text-align: center; margin-bottom: 15px;">
            <div style="font-size: 0.8rem; color: #BE9D5F;">المستخدم الحالي:</div>
            <div style="font-weight: 800; font-size: 1rem; color: #FFFFFF;">{current_user['full_name']}</div>
            <div style="font-size: 0.75rem; color: #E2E1DE;">الصلاحية: {user_role}</div>
        </div>
        <div style="height: 1px; background: #BE9D5F; margin-bottom: 12px;"></div>
    """, unsafe_allow_html=True)
    
    menu = st.sidebar.radio("التنقل السريع", allowed_menus)

    st.markdown("<br><hr style='border-color: rgba(190, 157, 95, 0.3);'>", unsafe_allow_html=True)
    if st.sidebar.button("🚪 تسجيل الخروج من النظام"):
        st.session_state.authenticated = False
        st.session_state.user_info = None
        st.rerun()

# ----------------------------------------------------
# ترويسة الصفحة الرسمية
# ----------------------------------------------------
logo_header_img = f'<img src="data:image/png;base64,{logo_b64}" style="height: 50px;">' if logo_b64 else ''
st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 15px; border-bottom: 2px solid #BE9D5F; padding-bottom: 12px; margin-bottom: 25px; direction: rtl;">
        {logo_header_img}
        <div>
            <h2 style="margin: 0; padding: 0; font-size: 1.7rem; color: #0F4733; font-weight: 800;">منظومة الإدارة والرقابة المالية</h2>
            <div style="color: #BE9D5F; font-size: 0.9rem; font-weight: 700; margin-top: 3px;">MA Real Estate Development &amp; Contracting</div>
        </div>
    </div>
""", unsafe_allow_html=True)

conn = get_connection()

# ====================================================
# 1. لوحة المؤشرات العامة والأرصدة
# ====================================================
if menu == "📊 لوحة المؤشرات العامة والأرصدة":
    st.subheader("💵 حالة الصناديق والسيولة اللحظية")
    
    query_vaults = """
        SELECT 
            v.name AS vault_name,
            v.currency,
            COALESCE(SUM(CASE WHEN t.direction = 'IN' THEN t.amount ELSE -t.amount END), 0) AS current_balance
        FROM vaults v
        LEFT JOIN transactions t ON v.id = t.vault_id
        GROUP BY v.id, v.name, v.currency;
    """
    df_vaults = pd.read_sql(query_vaults, conn)
    
    col1, col2 = st.columns(2)
    with col1:
        usd_bal = df_vaults.loc[df_vaults['currency'] == 'USD', 'current_balance'].values[0] if not df_vaults.empty else 0
        st.markdown(f"""
            <div class="metric-card" style="border-right-color: #0F4733;">
                <div class="metric-title">رصيد الخزينة بالدولار الأمريكي (USD)</div>
                <div class="metric-value-usd">${usd_bal:,.2f}</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        syp_bal = df_vaults.loc[df_vaults['currency'] == 'SYP', 'current_balance'].values[0] if not df_vaults.empty else 0
        st.markdown(f"""
            <div class="metric-card" style="border-right-color: #BE9D5F;">
                <div class="metric-title">رصيد الخزينة بالليرة السورية (SYP)</div>
                <div class="metric-value-gold">{syp_bal:,.0f} <span style="font-size: 1.1rem; color: #44494B;">ل.س</span></div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🏗️ مؤشرات أداء المشاريع النشطة")
    query_proj_summary = """
        SELECT 
            p.name AS "المشروع",
            p.project_type AS "التصنيف",
            p.status AS "الحالة",
            COUNT(t.id) AS "عدد الحركات",
            COALESCE(SUM(CASE WHEN t.direction = 'OUT' THEN t.amount_usd ELSE 0 END), 0) AS "إجمالي المصروف ($)",
            COALESCE(SUM(CASE WHEN t.direction = 'IN' THEN t.amount_usd ELSE 0 END), 0) AS "إجمالي المقبوض ($)"
        FROM projects p
        LEFT JOIN transactions t ON p.id = t.project_id
        GROUP BY p.id, p.name, p.project_type, p.status;
    """
    df_proj_summary = pd.read_sql(query_proj_summary, conn)
    st.dataframe(df_proj_summary, use_container_width=True)

# ====================================================
# 2. هيكل الشركاء ورأس المال والأرباح
# ====================================================
elif menu == "🤝 هيكل الشركاء ورأس المال والأرباح":
    st.subheader("🤝 هيكل ملكية الشركة وحساب الحصص تلقائياً بدون غش")
    
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(SUM(ROUND(t.amount_usd * p.management_fee_rate, 2)), 0)
        FROM projects p
        JOIN transactions t ON p.id = t.project_id
        WHERE t.direction = 'OUT' AND p.project_type != 'Internal';
    """)
    total_company_profit = float(cur.fetchone()[0])

    cur.execute("SELECT partner_equity_pct, salary_amount, salary_currency FROM stakeholders WHERE name = 'حمزة ديب';")
    h_data = cur.fetchone()
    hamza_pct = float(h_data[0]) if (h_data and h_data[0] is not None and float(h_data[0]) > 0) else 15.00
    hamza_sal = float(h_data[1]) if h_data and h_data[1] is not None else 0.00
    hamza_sal_curr = h_data[2] if h_data and h_data[2] else 'USD'

    # حساب رأس مال مصعب
    cur.execute("""
        SELECT COALESCE(SUM(amount_usd), 0)
        FROM transactions t
        LEFT JOIN stakeholders s ON t.stakeholder_id = s.id
        WHERE (s.name = 'مصعب المصري' OR t.description LIKE '%مصعب%')
          AND t.tx_type IN ('ايراد عام', 'مصروف عام') AND t.description LIKE '%راس مال%';
    """)
    mosab_capital = float(cur.fetchone()[0])
    if mosab_capital <= 0:
        mosab_capital = 11435.00

    # حساب رأس مال سامر (يشمل أي دفعات رأس مال جديدة)
    cur.execute("""
        SELECT COALESCE(SUM(amount_usd), 0)
        FROM transactions t
        LEFT JOIN stakeholders s ON t.stakeholder_id = s.id
        WHERE (s.name = 'سامر ديب' OR t.description LIKE '%سامر%')
          AND t.tx_type = 'ايراد عام';
    """)
    samer_capital = float(cur.fetchone()[0])
    if samer_capital <= 0:
        samer_capital = 1814.00

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
        st.markdown(f"""
            <div class="metric-card" style="border-right-color: #0F4733;">
                <div class="metric-title">إجمالي رأس المال التأسيسي المدفوع</div>
                <div class="metric-value-usd">${total_financial_capital:,.2f}</div>
            </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
            <div class="metric-card" style="border-right-color: #BE9D5F;">
                <div class="metric-title">أرباح أتعاب الإدارة المتراكمة</div>
                <div class="metric-value-gold">${total_company_profit:,.2f}</div>
            </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
            <div class="metric-card" style="border-right-color: #44494B;">
                <div class="metric-title">حصة حمزة ديب الإدارية المحمية</div>
                <div class="metric-value-usd" style="color: #BE9D5F;">{hamza_pct:.2f}%</div>
            </div>
        """, unsafe_allow_html=True)

    partners_breakdown = [
        {
            "الشريك": "مصعب المصري",
            "صفة الشراكة": "صاحب ومؤسس الشركة (شريك مالي وإداري)",
            "المساهمة في رأس المال ($)": f"${mosab_capital:,.2f}",
            "نسبة المساهمة المالية": f"{(mosab_capital/total_financial_capital*100):.1f}%",
            "نسبة الملكية الإجمالية من الشركة": f"{mosab_pct:.2f}%",
            "حصة الأرباح المحققة ($)": f"${(total_company_profit * mosab_pct / 100.0):,.2f}",
            "ملاحظات": "تُحسب آلياً من رأس المال بعد استقطاع حصة الإدارة"
        },
        {
            "الشريك": "سامر ديب",
            "صفة الشراكة": "مساهم برأس المال وشريك",
            "المساهمة في رأس المال ($)": f"${samer_capital:,.2f}",
            "نسبة المساهمة المالية": f"{(samer_capital/total_financial_capital*100):.1f}%",
            "نسبة الملكية الإجمالية من الشركة": f"{samer_pct:.2f}%",
            "حصة الأرباح المحققة ($)": f"${(total_company_profit * samer_pct / 100.0):,.2f}",
            "ملاحظات": "تُحسب نسبته آلياً بالمليم حسب مساهمته النقدية"
        },
        {
            "الشريك": "حمزة ديب",
            "صفة الشراكة": "شريك إداري (Sweat Equity) + موظف رسمي",
            "المساهمة في رأس المال ($)": "$0.00 (بدون مساهمة نقدية)",
            "نسبة المساهمة المالية": "0.0%",
            "نسبة الملكية الإجمالية من الشركة": f"{hamza_pct:.2f}%",
            "حصة الأرباح المحققة ($)": f"${(total_company_profit * hamza_pct / 100.0):,.2f}",
            "ملاحظات": f"راتب شهري مسجل: {hamza_sal:,.0f} {hamza_sal_curr} + النسبة الثابتة"
        }
    ]
    st.dataframe(pd.DataFrame(partners_breakdown), use_container_width=True)

    cur.execute("UPDATE stakeholders SET partner_equity_pct = %s WHERE name = 'مصعب المصري';", (round(mosab_pct, 2),))
    cur.execute("UPDATE stakeholders SET partner_equity_pct = %s WHERE name = 'سامر ديب';", (round(samer_pct, 2),))
    cur.execute("UPDATE stakeholders SET partner_equity_pct = %s WHERE name = 'حمزة ديب';", (round(hamza_pct, 2),))
    conn.commit()
    cur.close()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### ⚙️ تعديل نسبة وراتب حمزة ديب في أي وقت")
    with st.form("update_hamza_form"):
        col_h1, col_h2, col_h3 = st.columns(3)
        with col_h1:
            new_h_pct = st.number_input("نسبة حمزة ديب من أرباح الشركة %", min_value=1.0, max_value=50.0, value=float(hamza_pct), step=1.0)
        with col_h2:
            new_h_sal = st.number_input("الراتب الشهري كموظف", min_value=0.0, value=float(hamza_sal), step=50.0)
        with col_h3:
            new_h_curr = st.selectbox("عملة الراتب", ["USD", "SYP"], index=0 if hamza_sal_curr == "USD" else 1)

        if st.form_submit_button("💾 تحديث النسبة والراتب وإعادة الحساب فوراً"):
            cur = conn.cursor()
            cur.execute("""
                UPDATE stakeholders 
                SET partner_equity_pct = %s, salary_amount = %s, salary_currency = %s, role = 'Partner'
                WHERE name = 'حمزة ديب';
            """, (new_h_pct, new_h_sal, new_h_curr))
            conn.commit()
            cur.close()
            st.success(f"تم اعتماد نسبة {new_h_pct}% لحمزة ديب وإعادة احتساب الحصص تلقائياً!")
            st.rerun()

# ====================================================
# 3. كشوفات حسابات المستثمرين التفصيلية
# ====================================================
elif menu == "📑 كشوفات حسابات المستثمرين":
    st.subheader("📑 كشوفات حسابات المستثمرين والعملاء")
    st.caption("متابعة تدفقات ومستحقات كل مستثمر على حدة، وتفاصيل تنفيذ مشروعه وطباعة كشف الحساب:")

    inv_df = pd.read_sql("SELECT id, name FROM stakeholders WHERE role IN ('Investor', 'General') ORDER BY name;", conn)
    all_projs = pd.read_sql("SELECT id, name, management_fee_rate FROM projects WHERE project_type != 'Internal' ORDER BY name;", conn)

    if not all_projs.empty:
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            selected_proj_name = st.selectbox("اختر المشروع المطلوب كشف حسابه", all_projs['name'].tolist())
            proj_info = all_projs[all_projs['name'] == selected_proj_name].iloc[0]
            proj_id = int(proj_info['id'])
            fee_rate = float(proj_info['management_fee_rate'])
        
        with col_s2:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT s.name 
                FROM transactions t 
                JOIN stakeholders s ON t.stakeholder_id = s.id 
                WHERE t.project_id = %s AND (t.tx_type LIKE %s OR s.role = 'Investor');
            """, (proj_id, '%مقبوضات%'))
            linked_invs = [r[0] for r in cur.fetchall()]
            cur.close()

            default_inv = linked_invs[0] if linked_invs else (inv_df['name'].tolist()[0] if not inv_df.empty else "العميل / المستثمر")
            investor_name = st.selectbox("المستثمر المرتبط بالمشروع", linked_invs if linked_invs else [default_inv])

        cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(amount_usd), 0) FROM transactions WHERE project_id = %s AND direction = 'IN';", (proj_id,))
        total_paid_in = float(cur.fetchone()[0])

        cur.execute("SELECT COALESCE(SUM(amount_usd), 0) FROM transactions WHERE project_id = %s AND direction = 'OUT';", (proj_id,))
        total_costs_out = float(cur.fetchone()[0])
        cur.close()

        mgmt_fee_amount = total_costs_out * fee_rate
        total_claim = total_costs_out + mgmt_fee_amount
        net_balance = total_claim - total_paid_in

        st.markdown("---")
        c_inv1, c_inv2, c_inv3, c_inv4 = st.columns(4)
        with c_inv1:
            st.metric("إجمالي مقبوضات المستثمر", f"${total_paid_in:,.2f}")
        with c_inv2:
            st.metric("تكاليف ومواد التنفيذ", f"${total_costs_out:,.2f}")
        with c_inv3:
            st.metric(f"أتعاب الإدارة ({fee_rate*100:.0f}%)", f"${mgmt_fee_amount:,.2f}")
        with c_inv4:
            balance_label = "مستحق على المستثمر" if net_balance >= 0 else "رصيد فائض للمستثمر"
            st.metric(f"الصافي ({balance_label})", f"${abs(net_balance):,.2f}")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 🔍 جدول السجلات والحركات المالية للمشروع")
        
        query_inv_tx = """
            SELECT 
                t.id AS "رقم الفاتورة",
                t.tx_date AS "التاريخ",
                t.tx_type AS "نوع الحركة",
                t.direction AS "الاتجاه",
                t.amount AS "المبلغ",
                t.currency AS "العملة",
                t.amount_usd AS "المعادل بالدولار $",
                t.payment_method AS "طريقة الدفع",
                s.name AS "الطرف / المستفيد",
                t.description AS "البيان والتفاصيل"
            FROM transactions t
            LEFT JOIN stakeholders s ON t.stakeholder_id = s.id
            WHERE t.project_id = %s
            ORDER BY t.tx_date DESC, t.id DESC;
        """
        df_inv_tx = pd.read_sql(query_inv_tx, conn, params=(proj_id,))
        st.dataframe(df_inv_tx, use_container_width=True)

        col_dn1, col_dn2 = st.columns(2)
        with col_dn1:
            stats_dict = {
                'paid': total_paid_in,
                'costs': total_costs_out,
                'fee_rate': int(fee_rate * 100),
                'fees': mgmt_fee_amount,
                'balance': net_balance
            }
            tx_raw_list = [
                [r['رقم الفاتورة'], r['التاريخ'], r['نوع الحركة'], r['الاتجاه'], r['المبلغ'], r['العملة'], r['المعادل بالدولار $'], r['طريقة الدفع']]
                for _, r in df_inv_tx.iterrows()
            ]
            pdf_inv_bytes = generate_investor_statement_pdf(investor_name, selected_proj_name, stats_dict, tx_raw_list)
            st.download_button(
                label="📥 تحميل كشف الحساب كـ PDF",
                data=pdf_inv_bytes,
                file_name=f"Statement_{investor_name}_{selected_proj_name}.pdf",
                mime="application/pdf"
            )

        with col_dn2:
            excel_inv_data = to_excel_download_link(df_inv_tx, "Investor_Statement.xlsx")
            st.download_button(
                label="📥 تصدير كشف الحساب إلى Excel",
                data=excel_inv_data,
                file_name=f"Statement_{investor_name}_{selected_proj_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("لا توجد مشاريع مسجلة حالياً.")

# ====================================================
# 4. التحويل بين الخزائن والصرافة
# ====================================================
elif menu == "💱 التحويل بين الخزائن والصرافة":
    st.subheader("💱 التحويل المالي والصرافة بين الصناديق (USD ⮂ SYP)")
    st.caption("تسجيل عمليات تحويل الأموال أو تبديل العملات مع تحديث لحظي لأرصدة الصندوقين بقيد مزدوج متوازن:")

    query_v_bal = """
        SELECT v.id, v.name, v.currency,
               COALESCE(SUM(CASE WHEN t.direction = 'IN' THEN t.amount ELSE -t.amount END), 0) AS balance
        FROM vaults v
        LEFT JOIN transactions t ON v.id = t.vault_id
        GROUP BY v.id, v.name, v.currency;
    """
    df_v_bal = pd.read_sql(query_v_bal, conn)
    usd_available = df_v_bal.loc[df_v_bal['currency'] == 'USD', 'balance'].values[0] if not df_v_bal.empty else 0.0
    syp_available = df_v_bal.loc[df_v_bal['currency'] == 'SYP', 'balance'].values[0] if not df_v_bal.empty else 0.0
    usd_vault_id = int(df_v_bal.loc[df_v_bal['currency'] == 'USD', 'id'].values[0]) if not df_v_bal.empty else 1
    syp_vault_id = int(df_v_bal.loc[df_v_bal['currency'] == 'SYP', 'id'].values[0]) if not df_v_bal.empty else 2

    c_bal1, c_bal2 = st.columns(2)
    with c_bal1:
        st.info(f"💵 الرصيد المتاح في خزينة الدولار: **${usd_available:,.2f}**")
    with c_bal2:
        st.info(f"🪙 الرصيد المتاح في خزينة الليرة: **{syp_available:,.0f} ل.س**")

    st.markdown("---")
    
    with st.form("transfer_vault_form"):
        st.markdown("#### 📝 بيانات عملية الصرافة والتحويل")
        ct1, ct2, ct3 = st.columns(3)
        
        with ct1:
            tx_direction = st.selectbox(
                "اتجاه العملية",
                [
                    "من دولار (USD) إلى ليرة سورية (SYP) - صرافة لصالح الليرة",
                    "من ليرة سورية (SYP) إلى دولار (USD) - شراء دولار"
                ]
            )
            transfer_date = st.date_input("تاريخ العملية", datetime.now().date())

        with ct2:
            if "من دولار (USD) إلى ليرة" in tx_direction:
                from_currency = "USD"
                to_currency = "SYP"
                source_amount = st.number_input("المبلغ المراد تحويله من الدولار ($)", min_value=0.0, value=0.0, step=50.0)
                exchange_rate = st.number_input("سعر صرف الليرة مقابل الدولار", min_value=1.0, value=131.0, step=1.0)
                target_amount = source_amount * exchange_rate
            else:
                from_currency = "SYP"
                to_currency = "USD"
                source_amount = st.number_input("المبلغ المراد تحويله من الليرة (ل.س)", min_value=0.0, value=0.0, step=50000.0)
                exchange_rate = st.number_input("سعر صرف الدولار مقابل الليرة", min_value=1.0, value=131.0, step=1.0)
                target_amount = source_amount / exchange_rate if exchange_rate > 0 else 0.0

        with ct3:
            st.markdown(f"**المبلغ المستلم المقابل في الخزينة المستهدفة:**")
            if to_currency == "SYP":
                st.markdown(f"<div style='font-size: 1.8rem; font-weight: 800; color: #BE9D5F;'>{target_amount:,.0f} ل.س</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='font-size: 1.8rem; font-weight: 800; color: #0F4733;'>${target_amount:,.2f} USD</div>", unsafe_allow_html=True)
            transfer_notes = st.text_input("ملاحظات / اسم مكتب الصرافة أو الجهة", value="عملية صرافة داخلية بين الصناديق")

        submit_transfer = st.form_submit_button("🚀 اعتماد وترحيل عملية الصرافة بين الصندوقين")

        if submit_transfer:
            avail = usd_available if from_currency == "USD" else syp_available
            if source_amount <= 0:
                st.error("يرجى إدخال مبلغ أكبر من الصفر لإتمام التحويل.")
            elif source_amount > avail:
                st.error(f"المبلغ المطلوب ({source_amount:,.2f} {from_currency}) يتجاوز الرصيد المتوفر في الخزينة ({avail:,.2f} {from_currency})!")
            else:
                cur = conn.cursor()
                try:
                    timestamp_id = int(datetime.now().timestamp())
                    tx_out_id = f"TRF-OUT-{timestamp_id}"
                    tx_in_id = f"TRF-IN-{timestamp_id}"

                    src_v_id = usd_vault_id if from_currency == "USD" else syp_vault_id
                    dst_v_id = syp_vault_id if to_currency == "SYP" else usd_vault_id
                    amt_usd_equiv = source_amount if from_currency == "USD" else target_amount

                    cur.execute("""
                        INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description)
                        VALUES (%s, %s, 'تحويل بين الصناديق (صادر)', 1, 1, %s, %s, %s, %s, %s, 'OUT', 'صرافة وتحويل', %s);
                    """, (tx_out_id, transfer_date, src_v_id, source_amount, from_currency, exchange_rate, amt_usd_equiv, f"تحويل إلى خزينة {to_currency} - مرجع: {tx_in_id} - {transfer_notes}"))

                    cur.execute("""
                        INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description)
                        VALUES (%s, %s, 'تحويل بين الصناديق (وارد)', 1, 1, %s, %s, %s, %s, %s, 'IN', 'صرافة وتحويل', %s);
                    """, (tx_in_id, transfer_date, dst_v_id, target_amount, to_currency, exchange_rate, amt_usd_equiv, f"استلام من خزينة {from_currency} - مرجع: {tx_out_id} - {transfer_notes}"))

                    conn.commit()
                    st.success(f"تم بنجاح ترحيل عملية الصرافة! تم خصم {source_amount:,.2f} {from_currency} وإيداع {target_amount:,.2f} {to_currency}.")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"حدث خطأ أثناء تنفيذ التحويل: {e}")
                finally:
                    cur.close()

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📑 سجل عمليات الصرافة والتحويل المنفذة")
    query_transfers_history = """
        SELECT 
            t.id AS "رقم الحركة",
            t.tx_date AS "التاريخ",
            t.tx_type AS "نوع الحركة",
            v.name AS "الخزينة",
            t.direction AS "الاتجاه",
            t.amount AS "المبلغ",
            t.currency AS "العملة",
            t.exchange_rate AS "سعر الصرف المعتمد",
            t.amount_usd AS "المعادل بالدولار ($)",
            t.description AS "البيان والربط"
        FROM transactions t
        JOIN vaults v ON t.vault_id = v.id
        WHERE t.tx_type LIKE '%تحويل بين الصناديق%'
        ORDER BY t.tx_date DESC, t.id DESC;
    """
    df_trf_hist = pd.read_sql(query_transfers_history, conn)
    st.dataframe(df_trf_hist, use_container_width=True)

# ====================================================
# 5. طباعة السندات وتصدير التقارير (PDF & Excel)
# ====================================================
elif menu == "🖨️ طباعة السندات وتصدير التقارير":
    st.subheader("🖨️ طباعة السندات المالية وتصدير التقارير")
    
    tab_pdf_print, tab_excel_export = st.tabs([
        "📄 طباعة سند مالي رسمي (PDF)",
        "📊 تصدير السجلات إلى Excel"
    ])

    with tab_pdf_print:
        st.markdown("### 📄 توليد سند قبض / صرف رسمي جاهز للطباعة")
        tx_options_df = pd.read_sql("""
            SELECT t.id, t.tx_date, t.amount, t.currency, s.name AS s_name, p.name AS p_name
            FROM transactions t
            LEFT JOIN stakeholders s ON t.stakeholder_id = s.id
            LEFT JOIN projects p ON t.project_id = p.id
            ORDER BY t.tx_date DESC, t.id DESC;
        """, conn)

        if not tx_options_df.empty:
            chosen_tx_id = st.selectbox("اختر رقم السند المطلوب طباعته", tx_options_df['id'].tolist())
            
            cur = conn.cursor()
            cur.execute("""
                SELECT t.id, t.tx_date, t.tx_type, p.name, s.name, t.amount, t.currency, t.exchange_rate, t.amount_usd, t.payment_method, t.description
                FROM transactions t
                LEFT JOIN projects p ON t.project_id = p.id
                LEFT JOIN stakeholders s ON t.stakeholder_id = s.id
                WHERE t.id = %s;
            """, (chosen_tx_id,))
            tx_r = cur.fetchone()
            
            tx_dict = {
                'id': tx_r[0],
                'tx_date': tx_r[1],
                'tx_type': tx_r[2],
                'project_name': tx_r[3],
                'stakeholder_name': tx_r[4],
                'amount': float(tx_r[5]),
                'currency': tx_r[6],
                'exchange_rate': float(tx_r[7]),
                'amount_usd': float(tx_r[8]),
                'payment_method': tx_r[9],
                'description': tx_r[10] or ''
            }

            cur.execute("""
                SELECT item_name, category, quantity, unit_price, total_price 
                FROM invoice_items WHERE transaction_id = %s;
            """, (chosen_tx_id,))
            items_r = cur.fetchall()
            cur.close()

            st.info(f"سند رقم: **{tx_dict['id']}** | المستفيد: **{tx_dict['stakeholder_name']}** | المبلغ: **{tx_dict['amount']:,.2f} {tx_dict['currency']}**")

            pdf_bytes = generate_receipt_pdf(tx_dict, items_r)
            st.download_button(
                label="📥 تحميل السند الرسمي بصيغة PDF",
                data=pdf_bytes,
                file_name=f"Voucher_{tx_dict['id']}.pdf",
                mime="application/pdf"
            )
        else:
            st.info("لا توجد حركات مالية مسجلة للطباعة.")

    with tab_excel_export:
        st.markdown("### 📊 تصدير السجلات المالية والجداول إلى Excel بنقرة واحدة")
        
        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            st.markdown("#### 📑 دفتر الحركات المالية العام")
            df_export_tx = pd.read_sql("""
                SELECT t.id, t.tx_date, t.tx_type, p.name AS project, s.name AS party, t.amount, t.currency, t.exchange_rate, t.amount_usd, t.direction, t.payment_method, t.description
                FROM transactions t
                LEFT JOIN projects p ON t.project_id = p.id
                LEFT JOIN stakeholders s ON t.stakeholder_id = s.id
                ORDER BY t.tx_date DESC;
            """, conn)
            excel_tx_data = to_excel_download_link(df_export_tx, "transactions.xlsx")
            st.download_button(
                label="📥 تنزيل دفتر الفواتير (Excel)",
                data=excel_tx_data,
                file_name=f"MA_Transactions_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        with col_ex2:
            st.markdown("#### 🏗️ كشف حسابات وتكاليف المشاريع")
            df_export_proj = pd.read_sql("""
                SELECT p.name AS project, p.project_type, p.status, p.management_fee_rate,
                       COALESCE(SUM(CASE WHEN t.direction = 'OUT' THEN t.amount_usd ELSE 0 END), 0) AS total_costs_usd,
                       COALESCE(SUM(CASE WHEN t.direction = 'IN' THEN t.amount_usd ELSE 0 END), 0) AS total_received_usd
                FROM projects p
                LEFT JOIN transactions t ON p.id = t.project_id
                GROUP BY p.id, p.name, p.project_type, p.status, p.management_fee_rate;
            """, conn)
            excel_proj_data = to_excel_download_link(df_export_proj, "projects_summary.xlsx")
            st.download_button(
                label="📥 تنزيل كشف المشاريع (Excel)",
                data=excel_proj_data,
                file_name=f"MA_Projects_Summary_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        st.markdown("---")
        col_ex3, col_ex4 = st.columns(2)
        with col_ex3:
            st.markdown("#### 💳 مسيرات الرواتب الشهرية")
            df_export_pay = pd.read_sql("""
                SELECT p.payroll_month, s.name, p.base_salary, p.overtime_hours, p.overtime_amount, p.absence_days, p.deductions, p.net_salary, p.currency, p.transaction_id, p.paid_at
                FROM payroll_records p
                JOIN stakeholders s ON p.employee_id = s.id
                ORDER BY p.payroll_month DESC;
            """, conn)
            excel_pay_data = to_excel_download_link(df_export_pay, "payroll.xlsx")
            st.download_button(
                label="📥 تنزيل مسيرات الرواتب (Excel)",
                data=excel_pay_data,
                file_name=f"MA_Payroll_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        with col_ex4:
            st.markdown("#### 📦 رصيد ومواد المخزون")
            df_export_inv = pd.read_sql("SELECT item_name, category, quantity_on_hand, avg_unit_cost, currency, last_updated FROM inventory_stock ORDER BY item_name;", conn)
            excel_inv_data = to_excel_download_link(df_export_inv, "inventory.xlsx")
            st.download_button(
                label="📥 تنزيل جرد المخزون (Excel)",
                data=excel_inv_data,
                file_name=f"MA_Inventory_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# ====================================================
# 6. مسيرات الرواتب الشهرية المؤتمتة
# ====================================================
elif menu == "💳 مسيرات الرواتب الشهرية":
    st.subheader("💳 احتساب وصرف مسيرات الرواتب وربطها بالدوام")
    
    tab_pay_calc, tab_pay_history = st.tabs([
        "⚙️ احتساب وصرف راتب موظف لشهر محدد",
        "📑 سجل الرواتب المصروفة سابقاً"
    ])

    with tab_pay_calc:
        st.markdown("### 🧮 محرك احتساب الراتب الشهري")
        c_p1, c_p2 = st.columns(2)
        with c_p1:
            emps_sal = pd.read_sql("SELECT id, name, salary_amount, salary_currency FROM stakeholders WHERE role IN ('Employee', 'Partner') AND salary_amount > 0 ORDER BY name;", conn)
            if not emps_sal.empty:
                selected_emp_name = st.selectbox("اختر الموظف", emps_sal['name'].tolist())
                emp_record = emps_sal[emps_sal['name'] == selected_emp_name].iloc[0]
                emp_id = int(emp_record['id'])
                base_salary = float(emp_record['salary_amount'])
                currency = str(emp_record['salary_currency'])
            else:
                st.warning("لا يوجد موظفون محدد لهم رواتب أساسية.")
                emp_record = None

        with c_p2:
            current_month = datetime.now().strftime("%Y-%m")
            payroll_month = st.text_input("شهر المسير (صيغة YYYY-MM)", value=current_month)

        if emp_record is not None:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    COALESCE(SUM(overtime_hours), 0) AS total_ot,
                    COUNT(CASE WHEN status = 'غياب' THEN 1 END) AS absent_days
                FROM employee_attendance
                WHERE employee_id = %s AND TO_CHAR(work_date, 'YYYY-MM') = %s;
            """, (emp_id, payroll_month))
            att_data = cur.fetchone()
            ot_hours = float(att_data[0]) if att_data else 0.0
            absent_days = int(att_data[1]) if att_data else 0
            cur.close()

            hourly_rate = (base_salary / 240.0) if base_salary > 0 else 0.0
            daily_rate = (base_salary / 30.0) if base_salary > 0 else 0.0
            calculated_ot_amount = ot_hours * hourly_rate * 1.5
            calculated_deduction = absent_days * daily_rate

            st.markdown("---")
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.metric("الراتب الأساسي", f"{base_salary:,.2f} {currency}")
            with col_m2:
                st.metric("ساعات الإضافي", f"{ot_hours:.2f} س", f"+{calculated_ot_amount:,.2f} {currency}")
            with col_m3:
                st.metric("أيام الغياب", f"{absent_days} يوم", f"-{calculated_deduction:,.2f} {currency}", delta_color="inverse")
            with col_m4:
                net_salary = base_salary + calculated_ot_amount - calculated_deduction
                st.metric("صافي المستحق", f"{net_salary:,.2f} {currency}")

            cur = conn.cursor()
            cur.execute("SELECT id, paid_at, transaction_id FROM payroll_records WHERE employee_id = %s AND payroll_month = %s;", (emp_id, payroll_month))
            already_paid = cur.fetchone()
            cur.close()

            if already_paid:
                st.warning(f"⚠️ تم صرف راتب شهر {payroll_month} مسبقاً برقم فاتورة: `{already_paid[2]}`")
            else:
                with st.form("confirm_payout_form"):
                    st.markdown("#### 💵 اعتماد صرف الراتب")
                    c_f1, c_f2 = st.columns(2)
                    with c_f1:
                        payment_method = st.selectbox("طريقة التسليم", ["كاش", "حوالة"])
                        payout_date = st.date_input("تاريخ الصرف", datetime.now().date())
                    with c_f2:
                        payout_notes = st.text_input("ملاحظات السند", value=f"صرف راتب شهر {payroll_month} - {selected_emp_name}")

                    if st.form_submit_button("🚀 اعتماد الصرف وتحديث الخزينة"):
                        cur = conn.cursor()
                        try:
                            sal_tx_id = f"SAL-{payroll_month}-{emp_id}"
                            v_id = 1 if currency == 'USD' else 2
                            cur.execute("SELECT exchange_rate FROM transactions WHERE currency = 'SYP' ORDER BY tx_date DESC LIMIT 1;")
                            r_row = cur.fetchone()
                            syp_rate = float(r_row[0]) if r_row else 131.0
                            amt_usd = net_salary if currency == 'USD' else (net_salary / syp_rate)

                            cur.execute("""
                                INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description)
                                VALUES (%s, %s, 'راتب او سلفة', 1, %s, %s, %s, %s, %s, %s, 'OUT', %s, %s);
                            """, (sal_tx_id, payout_date, emp_id, v_id, net_salary, currency, syp_rate if currency == 'SYP' else 1.0, amt_usd, payment_method, payout_notes))

                            cur.execute("""
                                INSERT INTO payroll_records (employee_id, payroll_month, base_salary, overtime_hours, overtime_amount, absence_days, deductions, net_salary, currency, payment_status, transaction_id)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'معتمد ومصروف', %s);
                            """, (emp_id, payroll_month, base_salary, ot_hours, calculated_ot_amount, absent_days, calculated_deduction, net_salary, currency, sal_tx_id))

                            conn.commit()
                            st.success(f"تم بنجاح صرف راتب شهر {payroll_month}!")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"خطأ: {e}")
                        finally:
                            cur.close()

    with tab_pay_history:
        st.markdown("### 📋 سجل مسيرات الرواتب السابقة")
        query_pay_all = """
            SELECT 
                p.payroll_month AS "الشهر",
                s.name AS "الموظف",
                p.base_salary AS "الأساسي",
                p.overtime_hours AS "ساعات الإضافي",
                p.overtime_amount AS "قيمة الإضافي",
                p.absence_days AS "أيام الغياب",
                p.deductions AS "الخصومات",
                p.net_salary AS "صافي المستلم",
                p.currency AS "العملة",
                p.transaction_id AS "رقم السند المالي",
                p.paid_at::date AS "تاريخ الصرف"
            FROM payroll_records p
            JOIN stakeholders s ON p.employee_id = s.id
            ORDER BY p.payroll_month DESC, p.id DESC;
        """
        df_pay_history = pd.read_sql(query_pay_all, conn)
        st.dataframe(df_pay_history, use_container_width=True)

# ====================================================
# 7. جدول دوامات وساعات العمل
# ====================================================
elif menu == "⏱️ جدول دوامات وساعات العمل":
    st.subheader("⏱️ جدول متابعة دوام وساعات عمل الموظفين")
    
    tab_att_log, tab_att_new, tab_att_rep = st.tabs([
        "📋 سجل الدوام الشهري",
        "➕ تسجيل حضور / دوام يومي",
        "📊 ملخص ساعات العمل والغياب"
    ])

    with tab_att_log:
        col_fl1, col_fl2 = st.columns(2)
        emps_df = pd.read_sql("SELECT id, name FROM stakeholders WHERE role IN ('Employee', 'Partner') ORDER BY name;", conn)
        with col_fl1:
            emp_filter = st.selectbox("تصفية بحسب الموظف", ["الكل"] + emps_df['name'].tolist())
        with col_fl2:
            status_filter = st.selectbox("تصفية بحسب حالة الدوام", ["الكل", "حاضر", "متأخر", "غياب", "إجازة"])

        query_att = """
            SELECT 
                a.id AS "المعرف",
                s.name AS "الموظف",
                a.work_date AS "التاريخ",
                a.time_in AS "وقت الحضور",
                a.time_out AS "وقت الانصراف",
                a.total_hours AS "ساعات العمل",
                a.overtime_hours AS "إضافي (ساعة)",
                a.status AS "الحالة",
                a.notes AS "ملاحظات"
            FROM employee_attendance a
            JOIN stakeholders s ON a.employee_id = s.id
            WHERE 1=1
        """
        if emp_filter != "الكل":
            query_att += f" AND s.name = '{emp_filter}'"
        if status_filter != "الكل":
            query_att += f" AND a.status = '{status_filter}'"
            
        query_att += " ORDER BY a.work_date DESC, a.id DESC;"
        df_att = pd.read_sql(query_att, conn)
        st.dataframe(df_att, use_container_width=True)

    with tab_att_new:
        with st.form("new_attendance_form", clear_on_submit=True):
            ca1, ca2, ca3 = st.columns(3)
            with ca1:
                selected_emp_att = st.selectbox("الموظف", emps_df['name'].tolist())
                att_date = st.date_input("تاريخ اليوم", datetime.now().date())
                att_status = st.selectbox("حالة الدوام", ["حاضر", "متأخر", "غياب", "إجازة"])
            
            with ca2:
                t_in = st.time_input("وقت الدخول / الحضور", time(9, 0))
                t_out = st.time_input("وقت الخروج / الانصراف", time(17, 0))
                standard_hours = st.number_input("ساعات الدوام النظامية", min_value=1.0, max_value=12.0, value=8.0)

            with ca3:
                datetime_in = datetime.combine(datetime.today(), t_in)
                datetime_out = datetime.combine(datetime.today(), t_out)
                duration = (datetime_out - datetime_in).total_seconds() / 3600.0 if datetime_out >= datetime_in else 0.0
                calc_hours = duration if att_status in ["حاضر", "متأخر"] else 0.0
                calc_overtime = max(0.0, calc_hours - standard_hours)
                st.markdown(f"**ساعات العمل:** {calc_hours:.2f} س | **إضافي:** {calc_overtime:.2f} س")
                att_notes = st.text_area("ملاحظات")

            if st.form_submit_button("💾 حفظ قيد الدوام"):
                emp_id_val = int(emps_df.loc[emps_df['name'] == selected_emp_att, 'id'].values[0])
                cur = conn.cursor()
                try:
                    cur.execute("""
                        INSERT INTO employee_attendance (employee_id, work_date, time_in, time_out, total_hours, status, overtime_hours, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (employee_id, work_date) DO UPDATE SET
                            time_in = EXCLUDED.time_in, time_out = EXCLUDED.time_out,
                            total_hours = EXCLUDED.total_hours, status = EXCLUDED.status,
                            overtime_hours = EXCLUDED.overtime_hours, notes = EXCLUDED.notes;
                    """, (emp_id_val, att_date, t_in if att_status in ["حاضر", "متأخر"] else None, t_out if att_status in ["حاضر", "متأخر"] else None, calc_hours, att_status, calc_overtime, att_notes))
                    conn.commit()
                    st.success("تم حفظ الدوام بنجاح!")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"خطأ: {e}")
                finally:
                    cur.close()

    with tab_att_rep:
        query_rep = """
            SELECT 
                s.name AS "الموظف",
                COUNT(CASE WHEN a.status = 'حاضر' THEN 1 END) AS "أيام الحضور",
                COUNT(CASE WHEN a.status = 'غياب' THEN 1 END) AS "أيام الغياب",
                COALESCE(SUM(a.total_hours), 0) AS "إجمالي الساعات",
                COALESCE(SUM(a.overtime_hours), 0) AS "ساعات الإضافي"
            FROM stakeholders s
            LEFT JOIN employee_attendance a ON s.id = a.employee_id
            WHERE s.role IN ('Employee', 'Partner')
            GROUP BY s.id, s.name;
        """
        df_rep = pd.read_sql(query_rep, conn)
        st.dataframe(df_rep, use_container_width=True)

# ====================================================
# 8. إدارة المخزون ومواد المشاريع
# ====================================================
elif menu == "📦 إدارة المخزون ومواد المشاريع":
    st.subheader("📦 إدارة المستودع والمخزون المربوط بالفواتير")
    
    tab_stock, tab_issue, tab_history = st.tabs([
        "🧱 جرد المواد والمخزون المربوط",
        "📤 سحب مواد من المخزون إلى مشروع",
        "📑 سجل حركات وصرف المواد"
    ])

    with tab_stock:
        query_stock = """
            SELECT 
                s.item_name AS "اسم المادة / الصنف",
                s.category AS "التصنيف",
                s.quantity_on_hand AS "الكمية المتوفرة",
                s.avg_unit_cost AS "تكلفة الوحدة",
                ROUND(s.quantity_on_hand * s.avg_unit_cost, 2) AS "إجمالي القيمة التقديرية",
                s.currency AS "العملة",
                COUNT(i.id) AS "عدد مرات التوريد",
                s.last_updated::date AS "تاريخ التحديث"
            FROM inventory_stock s
            LEFT JOIN invoice_items i ON s.item_name = i.item_name
            GROUP BY s.id, s.item_name, s.category, s.quantity_on_hand, s.avg_unit_cost, s.currency, s.last_updated
            ORDER BY s.quantity_on_hand DESC;
        """
        df_stock = pd.read_sql(query_stock, conn)
        st.dataframe(df_stock, use_container_width=True)

    with tab_issue:
        df_avail = pd.read_sql("SELECT item_name, quantity_on_hand, avg_unit_cost, currency FROM inventory_stock WHERE quantity_on_hand > 0;", conn)
        active_projects = pd.read_sql("SELECT id, name FROM projects WHERE status = 'Active' AND project_type != 'Internal' ORDER BY name;", conn)

        if df_avail.empty or active_projects.empty:
            st.warning("لا توجد مواد متوفرة بالمستودع أو لا توجد مشاريع نشطة.")
        else:
            with st.form("issue_material_form"):
                ci1, ci2 = st.columns(2)
                with ci1:
                    selected_item = st.selectbox("المادة المراد صرفها", df_avail['item_name'].tolist())
                    item_info = df_avail[df_avail['item_name'] == selected_item].iloc[0]
                    st.caption(f"المتوفر: {item_info['quantity_on_hand']} | سعر الوحدة: {item_info['avg_unit_cost']} {item_info['currency']}")
                    issue_qty = st.number_input("الكمية", min_value=0.01, max_value=float(item_info['quantity_on_hand']), value=1.0)

                with ci2:
                    target_proj_name = st.selectbox("المشروع المستلم", active_projects['name'].tolist())
                    issue_date = st.date_input("التاريخ", datetime.now().date())
                    issue_notes = st.text_input("ملاحظات البند ومكان تركيبه")

                total_issue_cost = issue_qty * float(item_info['avg_unit_cost'])
                st.info(f"💰 التكلفة الإجمالية: **{total_issue_cost:,.2f} {item_info['currency']}**")

                if st.form_submit_button("🚀 اعتماد الصرف وتوليد الفاتورة"):
                    p_id = int(active_projects.loc[active_projects['name'] == target_proj_name, 'id'].values[0])
                    v_id = 1 if item_info['currency'] == 'USD' else 2
                    cur = conn.cursor()
                    try:
                        issue_inv_id = f"MAT-{int(datetime.now().timestamp())}"
                        cur.execute("SELECT exchange_rate FROM transactions WHERE currency = 'SYP' ORDER BY tx_date DESC LIMIT 1;")
                        r_row = cur.fetchone()
                        syp_rate = float(r_row[0]) if r_row else 131.0
                        amt_usd = total_issue_cost if item_info['currency'] == 'USD' else (total_issue_cost / syp_rate)

                        cur.execute("""
                            INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description)
                            VALUES (%s, %s, 'صرف مواد من المخزون', %s, 1, %s, %s, %s, %s, %s, 'OUT', 'صرف مخزني', %s);
                        """, (issue_inv_id, issue_date, p_id, v_id, total_issue_cost, item_info['currency'], syp_rate if item_info['currency'] == 'SYP' else 1.0, amt_usd, f"صرف {issue_qty} من {selected_item} إلى {target_proj_name} - {issue_notes}"))

                        cur.execute("""
                            INSERT INTO invoice_items (transaction_id, item_name, category, quantity, unit_price, total_price, currency, notes)
                            VALUES (%s, %s, 'مواد مسحوبة من المخزون', %s, %s, %s, %s, %s);
                        """, (issue_inv_id, selected_item, issue_qty, item_info['avg_unit_cost'], total_issue_cost, item_info['currency'], issue_notes))

                        cur.execute("""
                            UPDATE inventory_stock 
                            SET quantity_on_hand = quantity_on_hand - %s, last_updated = CURRENT_TIMESTAMP
                            WHERE item_name = %s;
                        """, (issue_qty, selected_item))

                        conn.commit()
                        st.success(f"تم صرف المواد وتوليد السند `{issue_inv_id}`!")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"خطأ: {e}")
                    finally:
                        cur.close()

    with tab_history:
        query_issues = """
            SELECT 
                t.id AS "رقم الفاتورة",
                t.tx_date AS "التاريخ",
                p.name AS "المشروع المستلم",
                i.item_name AS "المادة",
                i.quantity AS "الكمية",
                i.unit_price AS "سعر الوحدة",
                i.total_price AS "الإجمالي",
                i.currency AS "العملة",
                i.notes AS "ملاحظات"
            FROM invoice_items i
            JOIN transactions t ON i.transaction_id = t.id
            JOIN projects p ON t.project_id = p.id
            WHERE t.tx_type = 'صرف مواد من المخزون' OR i.category LIKE '%مخزون%'
            ORDER BY t.tx_date DESC;
        """
        df_issues = pd.read_sql(query_issues, conn)
        st.dataframe(df_issues, use_container_width=True)

# ====================================================
# 9. دليل وتعديل بيانات الأطراف
# ====================================================
elif menu == "👥 دليل وتعديل بيانات الأطراف":
    st.subheader("👥 دليل كافة الأطراف والجهات وتعديل بياناتهم")
    
    query_all_parties = """
        SELECT 
            s.id AS "المعرف",
            s.name AS "الاسم / الطرف",
            s.role AS "الدور",
            s.status AS "الحالة",
            s.salary_amount AS "الراتب",
            s.salary_currency AS "عملة الراتب",
            s.partner_equity_pct AS "نسبة الشراكة %",
            s.phone AS "رقم الهاتف",
            COUNT(t.id) AS "إجمالي الحركات",
            COALESCE(SUM(t.amount_usd), 0) AS "إجمالي المبالغ ($)"
        FROM stakeholders s
        LEFT JOIN transactions t ON s.id = t.stakeholder_id
        GROUP BY s.id, s.name, s.role, s.status, s.salary_amount, s.salary_currency, s.partner_equity_pct, s.phone
        ORDER BY s.id ASC;
    """
    df_parties = pd.read_sql(query_all_parties, conn)
    st.dataframe(df_parties, use_container_width=True)

    st.markdown("<br><hr>", unsafe_allow_html=True)
    st.markdown("### ✏️ تعديل بيانات طرف مسجل")
    party_names = df_parties["الاسم / الطرف"].tolist()
    selected_party_name = st.selectbox("اختر الطرف المطلوب تعديله:", [""] + party_names)

    if selected_party_name:
        cur = conn.cursor()
        cur.execute("SELECT id, name, role, status, salary_amount, salary_currency, partner_equity_pct, phone, notes FROM stakeholders WHERE name = %s;", (selected_party_name,))
        p_data = cur.fetchone()
        cur.close()

        if p_data:
            p_id, cur_name, cur_role, cur_status, cur_sal, cur_sal_curr, cur_equity, cur_phone, cur_notes = p_data
            role_options = ["General", "Employee", "Investor", "Partner"]
            status_options = ["نشط", "مفصول", "مستقيل", "عقد منتهي", "شريك سابق"]

            with st.form("edit_party_form"):
                cp1, cp2, cp3 = st.columns(3)
                with cp1:
                    new_name = st.text_input("اسم الطرف", value=cur_name if cur_name else "")
                    new_role = st.selectbox("الدور", role_options, index=role_options.index(cur_role) if cur_role in role_options else 0)
                    new_status = st.selectbox("الحالة", status_options, index=status_options.index(cur_status) if cur_status in status_options else 0)
                with cp2:
                    new_sal = st.number_input("الراتب", min_value=0.0, value=float(cur_sal) if cur_sal else 0.0, step=50.0)
                    new_sal_curr = st.selectbox("عملة الراتب", ["USD", "SYP"], index=0 if cur_sal_curr == "USD" else 1)
                    new_phone = st.text_input("الهاتف", value=cur_phone if cur_phone else "")
                with cp3:
                    new_equity = st.number_input("نسبة الشراكة %", min_value=0.0, max_value=100.0, value=float(cur_equity) if cur_equity else 0.0, step=1.0)
                    new_notes = st.text_area("ملاحظات", value=cur_notes if cur_notes else "")

                if st.form_submit_button("💾 حفظ التعديلات فوراً"):
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE stakeholders 
                        SET name = %s, role = %s, status = %s, salary_amount = %s, salary_currency = %s, partner_equity_pct = %s, phone = %s, notes = %s
                        WHERE id = %s;
                    """, (new_name.strip(), new_role, new_status, new_sal, new_sal_curr, new_equity, new_phone.strip(), new_notes.strip(), p_id))
                    conn.commit()
                    cur.close()
                    st.success("تم تحديث البيانات بنجاح!")
                    st.rerun()

# ====================================================
# 10. دفتر الحركات وسجل الفواتير
# ====================================================
elif menu == "📑 دفتر الحركات وسجل الفواتير":
    st.subheader("سجل العمليات المالية والتدقيق")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        currency_filter = st.selectbox("تصفية بحسب العملة", ["الكل", "USD", "SYP"])
    with col_f2:
        direction_filter = st.selectbox("تصفية الاتجاه المالي", ["الكل", "وارد (IN)", "صادر (OUT)"])

    base_query = """
        SELECT 
            t.id AS "رقم الفاتورة",
            t.tx_date AS "التاريخ",
            t.tx_type AS "نوع الحركة",
            p.name AS "المشروع",
            s.name AS "الطرف / المستفيد",
            t.amount AS "المبلغ",
            t.currency AS "العملة",
            t.exchange_rate AS "سعر الصرف",
            t.amount_usd AS "المعادل بالدولار $",
            t.direction AS "الاتجاه",
            t.payment_method AS "طريقة الدفع",
            t.description AS "البيان"
        FROM transactions t
        LEFT JOIN projects p ON t.project_id = p.id
        LEFT JOIN stakeholders s ON t.stakeholder_id = s.id
        WHERE 1=1
    """
    if currency_filter != "الكل":
        base_query += f" AND t.currency = '{currency_filter}'"
    if direction_filter == "وارد (IN)":
        base_query += " AND t.direction = 'IN'"
    elif direction_filter == "صادر (OUT)":
        base_query += " AND t.direction = 'OUT'"
        
    base_query += " ORDER BY t.tx_date DESC, t.id DESC;"
    df_tx = pd.read_sql(base_query, conn)
    st.dataframe(df_tx, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🔍 استعراض بنود فاتورة تفصيلية")
    all_inv_ids = df_tx["رقم الفاتورة"].tolist()
    search_inv = st.selectbox("اختر رقم الفاتورة", [""] + all_inv_ids)
    if search_inv:
        query_items = f"""
            SELECT item_name AS "اسم البند / المادة", category AS "التصنيف", quantity AS "الكمية", unit_price AS "سعر الوحدة", total_price AS "الإجمالي", currency AS "العملة", notes AS "ملاحظات"
            FROM invoice_items WHERE transaction_id = '{search_inv}';
        """
        df_items = pd.read_sql(query_items, conn)
        if not df_items.empty:
            st.dataframe(df_items, use_container_width=True)
        else:
            st.info("سند مالي مباشر لا يتضمن بنود مواد تفصيلية.")

# ====================================================
# 11. إضافة فاتورة وحركة متعددة البنود
# ====================================================
elif menu == "➕ إضافة فاتورة وحركة متعددة البنود":
    st.subheader("📄 تسجيل حركة مالية جديدة بفاتورة متعددة البنود")
    
    projects_df = pd.read_sql("SELECT id, name FROM projects ORDER BY name;", conn)
    stakeholders_df = pd.read_sql("SELECT id, name FROM stakeholders ORDER BY name;", conn)
    vaults_df = pd.read_sql("SELECT id, name, currency FROM vaults;", conn)

    st.markdown("#### 1️⃣ البيانات العامة للسند")
    c1, c2, c3 = st.columns(3)
    with c1:
        inv_id = st.text_input("رقم الفاتورة / السند (مثال: PAY-00050)")
        tx_date = st.date_input("تاريخ السند", datetime.now().date())
        tx_type = st.selectbox("نوع الحركة المالية", [
            "دفعة لمشروع", "شراء مواد وتخزين", "مقبوضات من مستثمر", "مصروف عام", "راتب او سلفة", "توزيع أرباح شريك", "ايراد عام"
        ])
    with c2:
        proj_idx = 0
        if tx_type == "شراء مواد وتخزين" and "مستودع الشركة والمخزون" in projects_df['name'].tolist():
            proj_idx = projects_df['name'].tolist().index("مستودع الشركة والمخزون")
        proj_name = st.selectbox("المشروع المرتبط / الوجهة", projects_df['name'].tolist(), index=proj_idx)
        party_name = st.selectbox("المورد / العميل / المستفيد", stakeholders_df['name'].tolist())
        method = st.selectbox("طريقة الدفع", ["كاش", "حوالة", "شيك"])
    with c3:
        currency = st.selectbox("العملة", ["USD", "SYP"])
        rate = st.number_input("سعر الصرف (لليرة السورية)", min_value=1.0, value=1.0 if currency == "USD" else 131.0)
        has_items = st.checkbox("هل تتضمن الفاتورة بنود ومواد تفصيلية؟", value=False)

    st.markdown("---")

    items_to_save = []
    final_amount = 0.0

    if has_items:
        st.markdown("#### 2️⃣ جدول بنود الفاتورة")
        num_items = st.number_input("عدد البنود", min_value=1, max_value=20, value=2, step=1)
        for i in range(int(num_items)):
            ci1, ci2, ci3, ci4, ci5 = st.columns([3, 2, 1.5, 2, 2])
            with ci1:
                it_name = st.text_input(f"اسم المادة #{i+1}", key=f"it_name_{i}")
            with ci2:
                it_cat = st.selectbox(f"التصنيف #{i+1}", ["مواد إكساء", "مصناعيات وورشات", "صحية وكهرباء", "عوازل", "نثريات"], key=f"it_cat_{i}")
            with ci3:
                it_qty = st.number_input(f"الكمية #{i+1}", min_value=0.01, value=1.0, key=f"it_qty_{i}")
            with ci4:
                it_price = st.number_input(f"سعر الوحدة ({currency}) #{i+1}", min_value=0.0, value=0.0, key=f"it_price_{i}")
            with ci5:
                sub_total = it_qty * it_price
                st.markdown(f"<div style='padding-top: 35px; font-weight: bold;'>الإجمالي: {sub_total:,.2f}</div>", unsafe_allow_html=True)
                final_amount += sub_total
                if it_name.strip():
                    items_to_save.append({"name": it_name.strip(), "cat": it_cat, "qty": it_qty, "price": it_price, "total": sub_total})
        st.info(f"💰 **إجمالي الفاتورة:** {final_amount:,.2f} {currency}")
    else:
        final_amount = st.number_input(f"إجمالي المبلغ المالي ({currency})", min_value=0.0, step=100.0)

    notes = st.text_area("البيان والملاحظات العامة")

    if st.button("💾 حفظ وترحيل الفاتورة مع كافة بنودها"):
        if not inv_id.strip() or final_amount <= 0:
            st.error("يرجى إدخال رقم الفاتورة ومبلغ أكبر من الصفر.")
        else:
            p_id = int(projects_df.loc[projects_df['name'] == proj_name, 'id'].values[0])
            s_id = int(stakeholders_df.loc[stakeholders_df['name'] == party_name, 'id'].values[0])
            v_id = int(vaults_df.loc[vaults_df['currency'] == currency, 'id'].values[0])
            direction = 'IN' if ('مقبوضات' in tx_type or 'ايراد' in tx_type) else 'OUT'
            amt_usd = final_amount if currency == 'USD' else (final_amount / rate if rate > 0 else 0)

            cur = conn.cursor()
            try:
                cur.execute("""
                    INSERT INTO transactions (id, tx_date, tx_type, project_id, stakeholder_id, vault_id, amount, currency, exchange_rate, amount_usd, direction, payment_method, description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (inv_id.strip(), tx_date, tx_type, p_id, s_id, v_id, final_amount, currency, rate, amt_usd, direction, method, notes))

                for it in items_to_save:
                    cur.execute("""
                        INSERT INTO invoice_items (transaction_id, item_name, category, quantity, unit_price, total_price, currency)
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """, (inv_id.strip(), it["name"], it["cat"], it["qty"], it["price"], it["total"], currency))

                    if proj_name == "مستودع الشركة والمخزون" or tx_type == "شراء مواد وتخزين":
                        cur.execute("""
                            INSERT INTO inventory_stock (item_name, category, quantity_on_hand, avg_unit_cost, currency, last_updated)
                            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (item_name) DO UPDATE SET
                                quantity_on_hand = inventory_stock.quantity_on_hand + EXCLUDED.quantity_on_hand,
                                avg_unit_cost = EXCLUDED.avg_unit_cost,
                                last_updated = CURRENT_TIMESTAMP;
                        """, (it["name"], it["cat"], it["qty"], it["price"], currency))

                conn.commit()
                st.success(f"تم ترحيل الفاتورة {inv_id} بنجاح!")
                st.rerun()
            except Exception as e:
                conn.rollback()
                st.error(f"خطأ أثناء الحفظ: {e}")
            finally:
                cur.close()

# ====================================================
# 12. تعديل / إلغاء حركة مالية
# ====================================================
elif menu == "✏️ تعديل / إلغاء حركة مالية":
    st.subheader("✏️ تعديل بيانات حركة مالية أو إلغاؤها")
    
    tx_list = pd.read_sql("SELECT id FROM transactions ORDER BY tx_date DESC, id DESC;", conn)['id'].tolist()
    selected_tx_id = st.selectbox("اختر رقم الفاتورة / السند", [""] + tx_list)

    if selected_tx_id:
        cur = conn.cursor()
        cur.execute("SELECT * FROM transactions WHERE id = %s;", (selected_tx_id,))
        row = cur.fetchone()
        colnames = [desc[0] for desc in cur.description]
        tx_data = dict(zip(colnames, row))
        cur.close()

        st.markdown("---")
        col_ed1, col_ed2 = st.columns([2, 1])
        with col_ed1:
            st.markdown(f"#### 📝 تعديل السند `{selected_tx_id}`")
            with st.form("edit_tx_form"):
                e_date = st.date_input("التاريخ", tx_data['tx_date'])
                e_amount = st.number_input("المبلغ", min_value=0.0, value=float(tx_data['amount']))
                e_rate = st.number_input("سعر الصرف", min_value=1.0, value=float(tx_data['exchange_rate']))
                e_notes = st.text_area("البيان", value=tx_data['description'] if tx_data['description'] else "")
                
                if st.form_submit_button("💾 حفظ التعديلات"):
                    amt_usd = e_amount if tx_data['currency'] == 'USD' else (e_amount / e_rate if e_rate > 0 else 0)
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE transactions 
                        SET tx_date = %s, amount = %s, exchange_rate = %s, amount_usd = %s, description = %s
                        WHERE id = %s;
                    """, (e_date, e_amount, e_rate, amt_usd, e_notes, selected_tx_id))
                    conn.commit()
                    cur.close()
                    st.success("تم تحديث البيانات بنجاح!")
                    st.rerun()

        with col_ed2:
            st.markdown("#### 🗑️ حذف الفاتورة")
            if st.button("تأكيد الحذف نهائياً", key="del_btn"):
                cur = conn.cursor()
                cur.execute("DELETE FROM transactions WHERE id = %s;", (selected_tx_id,))
                conn.commit()
                cur.close()
                st.success("تم الحذف بنجاح!")
                st.rerun()

# ====================================================
# 13. حسابات المشاريع والمستثمرين العامة
# ====================================================
elif menu == "🏢 حسابات المشاريع والمستثمرين":
    st.subheader("كشف حسابات المشاريع وأرباح الإدارة")
    
    query_projects_calc = """
        SELECT 
            p.name AS "المشروع",
            p.status AS "الحالة",
            p.management_fee_rate * 100 AS "أتعاب الإدارة %",
            COALESCE(SUM(CASE WHEN t.direction = 'OUT' THEN t.amount_usd ELSE 0 END), 0) AS "تكاليف التنفيذ ($)",
            ROUND(COALESCE(SUM(CASE WHEN t.direction = 'OUT' THEN t.amount_usd ELSE 0 END), 0) * p.management_fee_rate, 2) AS "أتعاب الإدارة المستحقة ($)",
            ROUND(COALESCE(SUM(CASE WHEN t.direction = 'OUT' THEN t.amount_usd ELSE 0 END), 0) * (1 + p.management_fee_rate), 2) AS "إجمالي المطالبة ($)",
            COALESCE(SUM(CASE WHEN t.direction = 'IN' THEN t.amount_usd ELSE 0 END), 0) AS "المقبوض من المستثمر ($)",
            ROUND(
                (COALESCE(SUM(CASE WHEN t.direction = 'OUT' THEN t.amount_usd ELSE 0 END), 0) * (1 + p.management_fee_rate)) - 
                COALESCE(SUM(CASE WHEN t.direction = 'IN' THEN t.amount_usd ELSE 0 END), 0)
            , 2) AS "صافي المستحق على المستثمر ($)"
        FROM projects p
        LEFT JOIN transactions t ON p.id = t.project_id
        WHERE p.project_type != 'Internal'
        GROUP BY p.id, p.name, p.status, p.management_fee_rate;
    """
    df_calc = pd.read_sql(query_projects_calc, conn)
    st.dataframe(df_calc, use_container_width=True)

# ====================================================
# 14. الإدارة والتشغيل والتعاقدات
# ====================================================
elif menu == "⚙️ الإدارة والتشغيل والتعاقدات":
    tab_emp, tab_proj, tab_inv = st.tabs([
        "👥 إدارة الموظفين والرواتب",
        "🏗️ إدارة المشاريع وإنهائها",
        "💼 المستثمرون والعقود"
    ])

    with tab_emp:
        df_emp = pd.read_sql("SELECT id, name AS \"اسم الموظف\", role AS \"المسمى\", salary_amount AS \"الراتب\", salary_currency AS \"العملة\", status AS \"الحالة\", phone AS \"الهاتف\" FROM stakeholders WHERE role IN ('Employee', 'Partner') ORDER BY id ASC;", conn)
        st.dataframe(df_emp, use_container_width=True)

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            st.markdown("#### ➕ إضافة موظف")
            with st.form("add_emp_form", clear_on_submit=True):
                e_name = st.text_input("اسم الموظف")
                e_phone = st.text_input("الهاتف")
                e_salary = st.number_input("الراتب", min_value=0.0, step=100.0)
                e_curr = st.selectbox("عملة الراتب", ["USD", "SYP"], key="emp_curr")
                if st.form_submit_button("إضافة"):
                    if e_name.strip():
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO stakeholders (name, role, phone, salary_amount, salary_currency, status)
                            VALUES (%s, 'Employee', %s, %s, %s, 'نشط')
                            ON CONFLICT (name) DO UPDATE SET salary_amount = EXCLUDED.salary_amount, status = 'نشط';
                        """, (e_name.strip(), e_phone.strip(), e_salary, e_curr))
                        conn.commit()
                        cur.close()
                        st.success("تم تسجيل الموظف!")
                        st.rerun()

        with col_e2:
            st.markdown("#### 🛑 تعديل حالة موظف")
            with st.form("status_emp_form"):
                active_emps = pd.read_sql("SELECT id, name FROM stakeholders WHERE role IN ('Employee', 'Partner');", conn)
                if not active_emps.empty:
                    selected_emp = st.selectbox("الموظف", active_emps['name'].tolist())
                    new_status = st.selectbox("الحالة الجديدة", ["نشط", "مفصول", "مستقيل"])
                    if st.form_submit_button("تحديث"):
                        cur = conn.cursor()
                        cur.execute("UPDATE stakeholders SET status = %s WHERE name = %s;", (new_status, selected_emp))
                        conn.commit()
                        cur.close()
                        st.success("تم التحديث!")
                        st.rerun()

    with tab_proj:
        df_p_all = pd.read_sql("SELECT id, name AS \"المشروع\", project_type AS \"النوع\", status AS \"الحالة\", management_fee_rate * 100 AS \"نسبة الإدارة %\" FROM projects ORDER BY id DESC;", conn)
        st.dataframe(df_p_all, use_container_width=True)

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("#### ➕ مشروع جديد")
            with st.form("add_project_form", clear_on_submit=True):
                p_name = st.text_input("اسم المشروع")
                p_type = st.selectbox("طبيعة المشروع", ["Finishing", "Development", "Internal"])
                p_fee = st.number_input("نسبة أتعاب الإدارة %", min_value=0.0, max_value=100.0, value=15.0)
                if st.form_submit_button("فتح المشروع"):
                    if p_name.strip():
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO projects (name, project_type, management_fee_rate, status)
                            VALUES (%s, %s, %s, 'Active')
                            ON CONFLICT (name) DO UPDATE SET status = 'Active', management_fee_rate = EXCLUDED.management_fee_rate;
                        """, (p_name.strip(), p_type, p_fee / 100.0))
                        conn.commit()
                        cur.close()
                        st.success("تم إنشاء المشروع!")
                        st.rerun()

        with col_p2:
            st.markdown("#### 🏁 إغلاق مشروع")
            with st.form("close_project_form"):
                active_projs = pd.read_sql("SELECT id, name FROM projects WHERE status = 'Active' AND project_type != 'Internal';", conn)
                if not active_projs.empty:
                    p_to_close = st.selectbox("المشروع المطلوب إغلاقه", active_projs['name'].tolist())
                    if st.form_submit_button("إغلاق"):
                        cur = conn.cursor()
                        cur.execute("UPDATE projects SET status = 'Completed', end_date = CURRENT_DATE WHERE name = %s;", (p_to_close,))
                        conn.commit()
                        cur.close()
                        st.success("تم إغلاق المشروع بنجاح!")
                        st.rerun()

    with tab_inv:
        df_inv_all = pd.read_sql("SELECT id, name AS \"اسم المستثمر\", status AS \"حالة العقد\", phone AS \"رقم الهاتف\" FROM stakeholders WHERE role = 'Investor' ORDER BY id DESC;", conn)
        st.dataframe(df_inv_all, use_container_width=True)

        col_i1, col_i2 = st.columns(2)
        with col_i1:
            st.markdown("#### ➕ إضافة مستثمر")
            with st.form("add_inv_form", clear_on_submit=True):
                i_name = st.text_input("اسم المستثمر")
                i_phone = st.text_input("رقم الهاتف")
                if st.form_submit_button("تسجيل"):
                    if i_name.strip():
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO stakeholders (name, role, phone, status)
                            VALUES (%s, 'Investor', %s, 'نشط')
                            ON CONFLICT (name) DO UPDATE SET role = 'Investor', status = 'نشط';
                        """, (i_name.strip(), i_phone.strip()))
                        conn.commit()
                        cur.close()
                        st.success("تم تسجيل المستثمر!")
                        st.rerun()

        with col_i2:
            st.markdown("#### 📝 إنهاء عقد مستثمر")
            with st.form("term_inv_form"):
                active_invs = pd.read_sql("SELECT id, name FROM stakeholders WHERE role = 'Investor' AND status = 'نشط';", conn)
                if not active_invs.empty:
                    i_to_term = st.selectbox("المستثمر", active_invs['name'].tolist())
                    if st.form_submit_button("إنهاء العقد"):
                        cur = conn.cursor()
                        cur.execute("UPDATE stakeholders SET status = 'عقد منتهي', termination_date = CURRENT_DATE WHERE name = %s;", (i_to_term,))
                        conn.commit()
                        cur.close()
                        st.success("تم إنهاء العقد.")
                        st.rerun()

conn.close()
