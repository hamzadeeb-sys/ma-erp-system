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
        # روابط CDN متعددة مع تجاوز حجب خوادم Streamlit Cloud
        urls = [
            "https://raw.githubusercontent.com/google/fonts/main/ofl/cairo/static/Cairo-Regular.ttf",
            "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/cairo/static/Cairo-Regular.ttf"
        ]
        for url in urls:
            try:
                req = urllib.request.Request(
                    url, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                with urllib.request.urlopen(req, timeout=12) as response, open(font_path, 'wb') as out_file:
                    out_file.write(response.read())
                if os.path.exists(font_path) and os.path.getsize(font_path) > 10000:
                    break
            except Exception:
                continue

    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont(FONT_NAME, font_path))
            return FONT_NAME
        except Exception:
            return "Helvetica"
    return "Helvetica"

CURRENT_PDF_FONT = setup_pdf_font()

def ar(text) -> str:
    """تشكيل المحارف العربية ومعالجة اتجاه النصوص ثنائية الاتجاه BiDi"""
    if text is None:
        return ""
    str_val = str(text).strip()
    if not str_val:
        return ""
    reshaped = arabic_reshaper.reshape(str_val)
    return get_display(reshaped)

def generate_receipt_pdf(tx_data: dict, items_data: list) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        rightMargin=25, 
        leftMargin=25, 
        topMargin=25, 
        bottomMargin=25
    )
    story = []
    styles = getSampleStyleSheet()

    # أنماط النصوص المعتمدة RTL
    title_style = ParagraphStyle(
        'MainTitle', 
        parent=styles['Heading1'], 
        fontName=CURRENT_PDF_FONT, 
        fontSize=15, 
        leading=22, 
        alignment=1, 
        textColor=colors.HexColor('#0F4733')
    )
    sub_title_style = ParagraphStyle(
        'SubTitle', 
        parent=styles['Normal'], 
        fontName=CURRENT_PDF_FONT, 
        fontSize=10.5, 
        leading=16, 
        alignment=1, 
        textColor=colors.HexColor('#BE9D5F')
    )
    table_cell_style = ParagraphStyle(
        'TableCellRTL',
        parent=styles['Normal'],
        fontName=CURRENT_PDF_FONT,
        fontSize=8.5,
        leading=12,
        alignment=2,
        textColor=colors.HexColor('#1F2328')
    )
    table_cell_center = ParagraphStyle(
        'TableCellCenter',
        parent=styles['Normal'],
        fontName=CURRENT_PDF_FONT,
        fontSize=8.5,
        leading=12,
        alignment=1,
        textColor=colors.HexColor('#1F2328')
    )
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName=CURRENT_PDF_FONT,
        fontSize=9,
        leading=13,
        alignment=1,
        textColor=colors.white
    )
    normal_style = ParagraphStyle(
        'NormalText', 
        parent=styles['Normal'], 
        fontName=CURRENT_PDF_FONT, 
        fontSize=9, 
        leading=14, 
        alignment=2, 
        textColor=colors.HexColor('#44494B')
    )

    story.append(Paragraph(ar("شركة MA للتطوير العقاري والمقاولات"), title_style))
    story.append(Paragraph(ar("سند مالي رسمي معتمد وموثق"), sub_title_style))
    story.append(Spacer(1, 12))

    # بيانات ترويسة السند
    header_data = [
        [Paragraph(ar(f"التاريخ: {tx_data.get('tx_date', '')}"), table_cell_style), Paragraph(ar(f"رقم السند: {tx_data.get('id', '')}"), table_cell_style)],
        [Paragraph(ar(f"المستفيد / الطرف: {tx_data.get('stakeholder_name', '')}"), table_cell_style), Paragraph(ar(f"المشروع: {tx_data.get('project_name', '')}"), table_cell_style)],
        [Paragraph(ar(f"طريقة الدفع: {tx_data.get('payment_method', '')}"), table_cell_style), Paragraph(ar(f"المبلغ: {tx_data.get('amount', 0):,.2f} {tx_data.get('currency', '')}"), table_cell_style)],
        [Paragraph(ar(f"نوع الحركة: {tx_data.get('tx_type', '')}"), table_cell_style), Paragraph(ar(f"المعادل بالدولار: ${tx_data.get('amount_usd', 0):,.2f} USD"), table_cell_style)]
    ]
    t_header = Table(header_data, colWidths=[270, 270])
    t_header.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F9F9F8')),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#BE9D5F')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 14))

    # جدول تفاصيل البنود مع حماية الالتفاف والتنسيق
    if items_data:
        story.append(Paragraph(ar("تفاصيل البنود والمواد المرفقة:"), normal_style))
        story.append(Spacer(1, 5))
        
        item_table_data = [[
            Paragraph(ar("الإجمالي"), table_header_style),
            Paragraph(ar("السعر الإفرادي"), table_header_style),
            Paragraph(ar("الكمية"), table_header_style),
            Paragraph(ar("التصنيف"), table_header_style),
            Paragraph(ar("اسم البند / المادة"), table_header_style)
        ]]
        
        for it in items_data:
            item_table_data.append([
                Paragraph(f"{float(it[4]):,.2f}", table_cell_center),
                Paragraph(f"{float(it[3]):,.2f}", table_cell_center),
                Paragraph(f"{float(it[2]):,.2f}", table_cell_center),
                Paragraph(ar(str(it[1])), table_cell_style),
                Paragraph(ar(str(it[0])), table_cell_style)
            ])
        
        t_items = Table(item_table_data, colWidths=[90, 90, 60, 110, 190])
        t_items.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F4733')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D0D7DE')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t_items)
        story.append(Spacer(1, 12))

    desc_text = tx_data.get('description', '')
    if desc_text:
        story.append(Paragraph(ar(f"البيان العام والملاحظات: {desc_text}"), normal_style))
        story.append(Spacer(1, 24))
    else:
        story.append(Spacer(1, 18))

    # تواقيع الاعتماد المالي
    sig_data = [[
        Paragraph(ar("توقيع المستلم"), table_cell_center), 
        Paragraph(ar("اعتماد الإدارة العامة"), table_cell_center), 
        Paragraph(ar("توقيع المحاسب المالي"), table_cell_center)
    ]]
    t_sig = Table(sig_data, colWidths=[180, 180, 180])
    t_sig.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), 1, colors.HexColor('#BE9D5F')),
        ('TOPPADDING', (0,0), (-1,-1), 20),
    ]))
    story.append(t_sig)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
