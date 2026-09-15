import io
import os
import urllib.request
import arabic_reshaper
from bidi.algorithm import get_display

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_NAME = "CairoFont"

def setup_pdf_font():
    font_path = "Cairo-Regular.ttf"
    if not os.path.exists(font_path):
        # تحميل خط Cairo الأصلي مع تمرير User-Agent لمنع خطأ HTTP 403 Forbidden من خوادم GitHub
        url = "https://raw.githubusercontent.com/google/fonts/main/ofl/cairo/static/Cairo-Regular.ttf"
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=10) as response, open(font_path, 'wb') as out_file:
                out_file.write(response.read())
        except Exception:
            pass

    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont(FONT_NAME, font_path))
            return FONT_NAME
        except Exception:
            return "Helvetica"
    return "Helvetica"

CURRENT_PDF_FONT = setup_pdf_font()

def ar(text) -> str:
    """إعادة تشكيل المحارف العربية وتطبيق خوارزمية BiDi مع التعامل الصارم مع النصوص الفارغة والأرقام"""
    if text is None:
        return ""
    str_val = str(text).strip()
    if not str_val:
        return ""
    reshaped = arabic_reshaper.reshape(str_val)
    return get_display(reshaped)

def generate_receipt_pdf(tx_data: dict, items_data: list) -> bytes:
    buffer = io.BytesIO()
    # هوامش A4 قياسية
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        rightMargin=30, 
        leftMargin=30, 
        topMargin=30, 
        bottomMargin=30
    )
    story = []
    styles = getSampleStyleSheet()

    # أنماط النصوص المتوافقة مع RTL
    title_style = ParagraphStyle(
        'MainTitle', 
        parent=styles['Heading1'], 
        fontName=CURRENT_PDF_FONT, 
        fontSize=16, 
        leading=22, 
        alignment=1, 
        textColor=colors.HexColor('#0F4733')
    )
    sub_title_style = ParagraphStyle(
        'SubTitle', 
        parent=styles['Normal'], 
        fontName=CURRENT_PDF_FONT, 
        fontSize=11, 
        leading=16, 
        alignment=1, 
        textColor=colors.HexColor('#BE9D5F')
    )
    section_label_style = ParagraphStyle(
        'SectionLabel',
        parent=styles['Normal'],
        fontName=CURRENT_PDF_FONT,
        fontSize=10,
        leading=14,
        alignment=2,
        textColor=colors.HexColor('#0F4733')
    )
    normal_style = ParagraphStyle(
        'NormalText', 
        parent=styles['Normal'], 
        fontName=CURRENT_PDF_FONT, 
        fontSize=9, 
        leading=13, 
        alignment=2, 
        textColor=colors.HexColor('#44494B')
    )

    story.append(Paragraph(ar("شركة MA للتطوير العقاري والمقاولات"), title_style))
    story.append(Paragraph(ar("سند مالي رسمي / إشعار قيد مالي"), sub_title_style))
    story.append(Spacer(1, 15))

    # ترويسة السند: ترتيب الأعمدة معكوس ليظهر من اليمين لليسار في RTL
    header_data = [
        [ar(f"التاريخ: {tx_data.get('tx_date', '')}"), ar(f"رقم السند: {tx_data.get('id', '')}")],
        [ar(f"الطرف / المستفيد: {tx_data.get('stakeholder_name', '')}"), ar(f"المشروع: {tx_data.get('project_name', '')}")],
        [ar(f"طريقة الدفع: {tx_data.get('payment_method', '')}"), ar(f"المبلغ: {tx_data.get('amount', 0):,.2f} {tx_data.get('currency', '')}")],
        [ar(f"نوع الحركة: {tx_data.get('tx_type', '')}"), ar(f"المعادل بالدولار: ${tx_data.get('amount_usd', 0):,.2f} USD")]
    ]
    t_header = Table(header_data, colWidths=[260, 260])
    t_header.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F9F9F8')),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#0F4733')),
        ('FONTNAME', (0,0), (-1,-1), CURRENT_PDF_FONT),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#BE9D5F'))
    ]))
    story.append(t_header)
    story.append(Spacer(1, 15))

    # جدول البنود التفصيلية (إن وجدت)
    if items_data:
        story.append(Paragraph(ar("تفاصيل البنود والمواد:"), section_label_style))
        story.append(Spacer(1, 6))
        
        # ترتيب الأعمدة في الـ Array: [اليمين: البند | التصنيف | الكمية | السعر | اليسار: الإجمالي]
        item_table_data = [[
            ar("الإجمالي"),
            ar("السعر"),
            ar("الكمية"),
            ar("التصنيف"),
            ar("البند / المادة")
        ]]
        for it in items_data:
            item_table_data.append([
                f"{float(it[4]):,.2f}",
                f"{float(it[3]):,.2f}",
                f"{float(it[2]):,.2f}",
                ar(str(it[1])),
                ar(str(it[0]))
            ])
        
        t_items = Table(item_table_data, colWidths=[85, 85, 60, 110, 180])
        t_items.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F4733')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,-1), CURRENT_PDF_FONT),
            ('FONTSIZE', (0,0), (-1,-1), 8.5),
            ('ALIGN', (0,0), (2,-1), 'CENTER'),
            ('ALIGN', (3,1), (-1,-1), 'RIGHT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E1DE')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t_items)
        story.append(Spacer(1, 15))

    # البيان العام والملاحظات
    desc_text = tx_data.get('description', '')
    if desc_text:
        story.append(Paragraph(ar(f"البيان العام والملاحظات: {desc_text}"), normal_style))
        story.append(Spacer(1, 30))
    else:
        story.append(Spacer(1, 20))

    # صندوق التواقيع والاعتمادات الرسمية
    sig_data = [[ar("توقيع المستلم:"), ar("اعتماد الإدارة:"), ar("توقيع المحاسب:")]]
    t_sig = Table(sig_data, colWidths=[175, 175, 175])
    t_sig.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), CURRENT_PDF_FONT),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#0F4733')),
        ('TOPPADDING', (0,0), (-1,-1), 18),
        ('LINEABOVE', (0,0), (-1,-1), 1, colors.HexColor('#BE9D5F'))
    ]))
    story.append(t_sig)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
