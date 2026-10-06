import io
from decimal import Decimal
from typing import Dict, Any, List
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def format_cop(val) -> str:
    try:
        return f"${float(val):,.2f} COP".replace(",", ".")
    except Exception:
        return f"${val} COP"

def generar_volante_pdf(detalle: Dict[str, Any], conceptos: List[Dict[str, Any]]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#1E293B'),
        alignment=1
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B'),
        alignment=1
    )
    section_style = ParagraphStyle(
        'DocSection',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#0F172A')
    )
    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )
    cell_bold = ParagraphStyle(
        'CellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0F172A')
    )

    elements = []

    # Encabezado
    elements.append(Paragraph("<b>PAYROLLFLOW FINANCIERA S.A.S.</b>", title_style))
    elements.append(Paragraph("NIT: 901.458.789-0 · Sistema Automatizado de Liquidación", subtitle_style))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(f"<b>VOLANTE INDIVIDUAL DE PAGO DE NÓMINA</b> — Periodo: {detalle.get('mes'):02d} / {detalle.get('anio')}", subtitle_style))
    elements.append(Spacer(1, 15))

    # Información del Empleado
    info_data = [
        [
            Paragraph("<b>Colaborador:</b>", cell_bold),
            Paragraph(f"{detalle.get('nombres')} {detalle.get('apellidos')}", cell_style),
            Paragraph("<b>Documento:</b>", cell_bold),
            Paragraph(str(detalle.get('documento')), cell_style),
        ],
        [
            Paragraph("<b>Cargo / Perfil:</b>", cell_bold),
            Paragraph(str(detalle.get('perfil')), cell_style),
            Paragraph("<b>Hijos Registrados:</b>", cell_bold),
            Paragraph(str(detalle.get('num_hijos')), cell_style),
        ],
        [
            Paragraph("<b>Horas Registradas:</b>", cell_bold),
            Paragraph(f"{float(detalle.get('horas_totales', 0)):.1f} h", cell_style),
            Paragraph("<b>Salario Base:</b>", cell_bold),
            Paragraph(format_cop(detalle.get('salario_base', 0)), cell_style),
        ]
    ]

    info_table = Table(info_data, colWidths=[100, 165, 110, 155])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 15))

    # Desglose de Conceptos
    elements.append(Paragraph("<b>Detalle de Devengados y Deducciones</b>", section_style))
    elements.append(Spacer(1, 6))

    conceptos_data = [
        [
            Paragraph("<b>Tipo</b>", cell_bold),
            Paragraph("<b>Concepto</b>", cell_bold),
            Paragraph("<b>Cant.</b>", cell_bold),
            Paragraph("<b>Vlr. Unitario</b>", cell_bold),
            Paragraph("<b>Total</b>", cell_bold)
        ]
    ]

    devengados_total = Decimal('0.00')
    deducciones_total = Decimal('0.00')

    for c in conceptos:
        tipo = c.get("tipo")
        if tipo in ("DEVENGADO", "BONIFICACION"):
            devengados_total += Decimal(str(c.get("valor_total", 0)))
        elif tipo == "DEDUCCION":
            deducciones_total += Decimal(str(c.get("valor_total", 0)))

        # Solo mostramos en el desprendible del empleado los conceptos del empleado (no aportes patronales que paga la empresa)
        if tipo in ("DEVENGADO", "BONIFICACION", "DEDUCCION"):
            tipo_label = "DEVENGADO" if tipo in ("DEVENGADO", "BONIFICACION") else "DEDUCCIÓN"
            conceptos_data.append([
                Paragraph(tipo_label, cell_style),
                Paragraph(c.get("concepto", ""), cell_style),
                Paragraph(f"{float(c.get('cantidad', 1)):.1f}", cell_style),
                Paragraph(format_cop(c.get("valor_unitario", 0)), cell_style),
                Paragraph(format_cop(c.get("valor_total", 0)), cell_bold)
            ])

    c_table = Table(conceptos_data, colWidths=[90, 200, 50, 95, 95])
    c_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(c_table)
    elements.append(Spacer(1, 12))

    # Resumen Financiero
    neto_val = Decimal(str(detalle.get("neto", 0)))
    totales_data = [
        [
            Paragraph("<b>(+) TOTAL DEVENGADO Y BENEFICIOS:</b>", cell_bold),
            Paragraph(format_cop(devengados_total), cell_bold)
        ],
        [
            Paragraph("<b>(-) TOTAL DEDUCCIONES DE LEY:</b>", cell_bold),
            Paragraph(format_cop(deducciones_total), cell_bold)
        ],
        [
            Paragraph("<b>(=) NETO A CONSIGNAR EN CUENTA:</b>", cell_bold),
            Paragraph(f"<b>{format_cop(neto_val)}</b>", cell_bold)
        ]
    ]

    t_table = Table(totales_data, colWidths=[340, 190])
    t_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#DCFCE7')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94A3B8')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(t_table)
    elements.append(Spacer(1, 40))

    # Firmas
    firmas_data = [
        [
            Paragraph("____________________________<br/><b>Firma del Empleador</b><br/>PayrollFlow RRHH", subtitle_style),
            Paragraph("____________________________<br/><b>Recibí Conforme</b><br/>C.C. " + str(detalle.get('documento')), subtitle_style)
        ]
    ]
    f_table = Table(firmas_data, colWidths=[265, 265])
    f_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(f_table)

    doc.build(elements)
    return buffer.getvalue()

def generar_consolidado_pdf(cabecera: Dict[str, Any], perfiles: List[Dict[str, Any]]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=30, leftMargin=30,
        topMargin=35, bottomMargin=35
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        textColor=colors.HexColor('#1E293B'),
        alignment=1
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#64748B'),
        alignment=1
    )
    cell_bold = ParagraphStyle('CB', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#0F172A'))
    cell_norm = ParagraphStyle('CN', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#334155'))

    elements = []
    elements.append(Paragraph("<b>INFORME FINANCIERO CONSOLIDADO DE NÓMINA</b>", title_style))
    elements.append(Paragraph(f"Periodo: {cabecera.get('mes'):02d}/{cabecera.get('anio')} · Estado: {cabecera.get('estado')}", subtitle_style))
    elements.append(Spacer(1, 15))

    # Tabla por perfil
    headers = ["Perfil", "Colab.", "Devengado", "Bonificaciones", "Deducciones", "Neto Empleados", "Aportes/Prest.", "Costo Real Empresa"]
    table_data = [[Paragraph(f"<b>{h}</b>", cell_bold) for h in headers]]

    tot_dev = sum((p.get('devengado', 0) for p in perfiles), 0)
    tot_bon = sum((p.get('bonificaciones', 0) for p in perfiles), 0)
    tot_ded = sum((p.get('deducciones_empleado', 0) for p in perfiles), 0)
    tot_net = sum((p.get('neto_pagado_empleados', 0) for p in perfiles), 0)
    tot_pat = sum(((p.get('aportes_patronales', 0) + p.get('prestaciones', 0)) for p in perfiles), 0)
    tot_cos = sum((p.get('costo_total_empresa', 0) for p in perfiles), 0)

    for p in perfiles:
        table_data.append([
            Paragraph(p.get("perfil", ""), cell_norm),
            Paragraph(str(p.get("empleados", 0)), cell_norm),
            Paragraph(format_cop(p.get("devengado", 0)), cell_norm),
            Paragraph(format_cop(p.get("bonificaciones", 0)), cell_norm),
            Paragraph(format_cop(p.get("deducciones_empleado", 0)), cell_norm),
            Paragraph(format_cop(p.get("neto_pagado_empleados", 0)), cell_norm),
            Paragraph(format_cop(p.get("aportes_patronales", 0) + p.get("prestaciones", 0)), cell_norm),
            Paragraph(format_cop(p.get("costo_total_empresa", 0)), cell_bold),
        ])

    table_data.append([
        Paragraph("<b>TOTAL</b>", cell_bold),
        Paragraph(str(sum((p.get('empleados', 0) for p in perfiles), 0)), cell_bold),
        Paragraph(format_cop(tot_dev), cell_bold),
        Paragraph(format_cop(tot_bon), cell_bold),
        Paragraph(format_cop(tot_ded), cell_bold),
        Paragraph(format_cop(tot_net), cell_bold),
        Paragraph(format_cop(tot_pat), cell_bold),
        Paragraph(format_cop(tot_cos), cell_bold),
    ])

    report_table = Table(table_data, colWidths=[65, 35, 65, 65, 65, 75, 75, 85])
    report_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FEF08A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(report_table)

    doc.build(elements)
    return buffer.getvalue()
