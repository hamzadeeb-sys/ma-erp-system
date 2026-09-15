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
        url = "https://github.com/google/fonts/raw/main/ofl/cairo/Cairo%5Bslnt%2Cwght%5D.ttf"
        try:
            urllib.request.urlretrieve(url, font_path)
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
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)

def generate_receipt_pdf(tx_data: dict, items_data: list) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('MainTitle', parent=styles['Heading1'], fontName=CURRENT_PDF_FONT, fontSize=16, leading=20, alignment=1, textColor=colors.HexColor('#0F4733'))
    sub_title_style = ParagraphStyle('SubTitle', parent=styles['Normal'], fontName=CURRENT_PDF_FONT, fontSize=11, leading=14, alignment=1, textColor=colors.HexColor('#BE9D5F'))
    normal_style = ParagraphStyle('NormalText', parent=styles['Normal'], fontName=CURRENT_PDF_FONT, fontSize=9, leading=13, alignment=2, textColor=colors.HexColor('#44494B'))

    story.append(Paragraph(ar("شركة MA للتطوير العقاري والمقاولات"), title_style))
    story.append(Paragraph(ar("سند مالي رسمي / إشعار قيد"), sub_title_style))
    story.append(Spacer(1, 15))

    header_data = [
        [ar(f"رقم السند: {tx_data['id']}"), ar(f"التاريخ: {tx_data['tx_date']}")],
        [ar(f"المشروع: {tx_data['project_name']}"), ar(f"الطرف: {tx_data['stakeholder_name']}")],
        [ar(f"المبلغ: {tx_data['amount']:,.2f} {tx_data['currency']}"), ar(f"طريقة الدفع: {tx_data['payment_method']}")],
        [ar(f"المعادل: ${tx_data['amount_usd']:,.2f} USD"), ar(f"نوع الحركة: {tx_data['tx_type']}")]
    ]
    t_header = Table(header_data, colWidths=[260, 260])
    t_header.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F9F9F8')),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#0F4733')),
        ('FONTNAME', (0,0), (-1,-1), CURRENT_PDF_FONT),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#BE9D5F'))
    ]))
    story.append(t_header)
    story.append(Spacer(1, 15))

    if items_data:
        story.append(Paragraph(ar("تفاصيل البنود والمواد:"), normal_style))
        story.append(Spacer(1, 5))
        item_table_data = [[ar("الإجمالي"), ar("السعر"), ar("الكمية"), ar("التصنيف"), ar("البند / البيان")]]
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
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E1DE')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_items)
        story.append(Spacer(1, 15))

    story.append(Paragraph(ar(f"البيان العام: {tx_data.get('description', '')}"), normal_style))
    story.append(Spacer(1, 30))

    sig_data = [[ar("توقيع المستلم:"), ar("اعتماد الإدارة:"), ar("توقيع المحاسب:")]]
    t_sig = Table(sig_data, colWidths=[175, 175, 175])
    t_sig.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), CURRENT_PDF_FONT),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#0F4733')),
        ('TOPPADDING', (0,0), (-1,-1), 20),
        ('LINEABOVE', (0,0), (-1,-1), 1, colors.HexColor('#BE9D5F'))
    ]))
    story.append(t_sig)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
