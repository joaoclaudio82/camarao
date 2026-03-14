"""
pdf_service.py – Geração de laudos PDF com ReportLab.
Suporta morfometria, larvas, motilidade e saúde.
"""
import io
import base64
import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF

# ── Paleta de cores ShrimpScan ───────────────────────────────────────────────
C_DARK    = colors.HexColor("#0a1628")
C_TEAL    = colors.HexColor("#00e5a0")
C_BLUE    = colors.HexColor("#00b4ff")
C_WARN    = colors.HexColor("#ffb300")
C_DANGER  = colors.HexColor("#ff4444")
C_LIGHT   = colors.HexColor("#e2f0ff")
C_MID     = colors.HexColor("#4a7a9b")
C_CARD    = colors.HexColor("#0f2040")
C_WHITE   = colors.white
C_GRAY    = colors.HexColor("#7a9abf")

# ── Estilos ───────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def _style(name, **kwargs):
    s = ParagraphStyle(name, **kwargs)
    return s

ST_TITLE   = _style("ss_title",   fontName="Helvetica-Bold",  fontSize=22, textColor=C_TEAL,  spaceAfter=4)
ST_SUB     = _style("ss_sub",     fontName="Helvetica-Bold",  fontSize=13, textColor=C_LIGHT, spaceAfter=2)
ST_BODY    = _style("ss_body",    fontName="Helvetica",       fontSize=9,  textColor=C_LIGHT, spaceAfter=2)
ST_SMALL   = _style("ss_small",   fontName="Helvetica",       fontSize=7.5,textColor=C_GRAY,  spaceAfter=1)
ST_CENTER  = _style("ss_center",  fontName="Helvetica",       fontSize=9,  textColor=C_LIGHT, alignment=TA_CENTER)
ST_METRIC  = _style("ss_metric",  fontName="Helvetica-Bold",  fontSize=18, textColor=C_TEAL,  alignment=TA_CENTER)
ST_LABEL   = _style("ss_label",   fontName="Helvetica",       fontSize=7,  textColor=C_GRAY,  alignment=TA_CENTER)
ST_ALERT   = _style("ss_alert",   fontName="Helvetica-Bold",  fontSize=8,  textColor=C_DANGER)
ST_OK      = _style("ss_ok",      fontName="Helvetica-Bold",  fontSize=8,  textColor=C_TEAL)
ST_WARN_S  = _style("ss_warns",   fontName="Helvetica-Bold",  fontSize=8,  textColor=C_WARN)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _header(elements, analysis_type: str, filename: str, proc_time: float):
    """Cabeçalho padrão do laudo."""
    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    type_labels = {
        "morphometry": "Morfometria por Imagem",
        "larvae":      "Análise de Larvas / PL",
        "motility":    "Motilidade por Vídeo",
        "health":      "Avaliação de Saúde",
    }
    type_icons = {"morphometry":"📏","larvae":"🔬","motility":"🎬","health":"❤️"}

    # Barra de título
    data = [[
        Paragraph("🦐  ShrimpScan", ST_TITLE),
        Paragraph(f"{type_icons.get(analysis_type,'')}  {type_labels.get(analysis_type, analysis_type)}", ST_SUB),
        Paragraph(f"<font color='#4a7a9b'>{now}</font>", ST_SMALL),
    ]]
    t = Table(data, colWidths=[5.5*cm, 8*cm, 4*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,-1), C_CARD),
        ("TOPPADDING",  (0,0),(-1,-1), 10),
        ("BOTTOMPADDING",(0,0),(-1,-1), 10),
        ("LEFTPADDING", (0,0),(-1,-1), 14),
        ("RIGHTPADDING",(0,0),(-1,-1), 14),
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
        ("ROUNDEDCORNERS", [6]),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 6))

    # Meta info
    meta = [[
        Paragraph(f"<b>Arquivo:</b> {filename or '—'}", ST_SMALL),
        Paragraph(f"<b>Tempo de proc.:</b> {proc_time}s", ST_SMALL),
        Paragraph(f"<b>Versão:</b> ShrimpScan v2.0 · OpenCV", ST_SMALL),
    ]]
    mt = Table(meta, colWidths=[7*cm, 5*cm, 5.5*cm])
    mt.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,-1), colors.HexColor("#0b1c3a")),
        ("TOPPADDING",  (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING", (0,0),(-1,-1), 12),
        ("RIGHTPADDING",(0,0),(-1,-1), 12),
    ]))
    elements.append(mt)
    elements.append(Spacer(1, 10))


def _metric_row(metrics: list) -> Table:
    """Linha de cards de métricas: [(label, value, color), ...]"""
    cells = []
    for label, value, col in metrics:
        c = colors.HexColor(col) if isinstance(col, str) else col
        cells.append([
            Paragraph(str(value), _style(f"mv_{label}", fontName="Helvetica-Bold",
                      fontSize=16, textColor=c, alignment=TA_CENTER)),
            Paragraph(label, ST_LABEL),
        ])
    n = len(cells)
    col_w = 17.5 * cm / n

    rows_data = [[c[0] for c in cells], [c[1] for c in cells]]
    t = Table(rows_data, colWidths=[col_w]*n)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#162850")),
        ("TOPPADDING",    (0,0),(  -1,0), 10),
        ("BOTTOMPADDING", (0,0),(  -1,0), 2),
        ("TOPPADDING",    (0,1),(  -1,1), 2),
        ("BOTTOMPADDING", (0,1),(  -1,1), 8),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("ROUNDEDCORNERS",[6]),
        ("LINEAFTER",     (0,0),(-2,-1), 0.5, colors.HexColor("#0a1628")),
    ]))
    return t


def _section(elements, title: str):
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=C_TEAL, spaceAfter=4))
    elements.append(Paragraph(title, ST_SUB))
    elements.append(Spacer(1, 4))


def _data_table(headers: list, rows: list) -> Table:
    """Tabela de dados com cabeçalho escuro."""
    all_rows = [headers] + rows
    n = len(headers)
    col_w = 17.5 * cm / n
    t = Table(all_rows, colWidths=[col_w]*n, repeatRows=1)
    style = [
        ("BACKGROUND",    (0,0),(-1, 0), C_CARD),
        ("TEXTCOLOR",     (0,0),(-1, 0), C_TEAL),
        ("FONTNAME",      (0,0),(-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 8),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.HexColor("#0f2040"), colors.HexColor("#0b1c3a")]),
        ("TEXTCOLOR",     (0,1),(-1,-1), C_LIGHT),
        ("GRID",          (0,0),(-1,-1), 0.3, colors.HexColor("#1e3a60")),
    ]
    t.setStyle(TableStyle(style))
    return t


def _b64_to_rl_image(b64str: str, max_w=17.5*cm, max_h=10*cm) -> Optional[RLImage]:
    """Converte base64 JPEG/PNG para Image do ReportLab."""
    if not b64str or "base64," not in b64str:
        return None
    try:
        data = base64.b64decode(b64str.split("base64,")[1])
        buf  = io.BytesIO(data)
        img  = RLImage(buf)
        # Escala proporcional
        ratio = min(max_w / img.drawWidth, max_h / img.drawHeight)
        img.drawWidth  *= ratio
        img.drawHeight *= ratio
        return img
    except Exception:
        return None


def _score_badge(score: float) -> str:
    """Retorna texto colorido com score."""
    if score >= 80:
        return f'<font color="#00e5a0"><b>{score}/100 ✓ Saudável</b></font>'
    elif score >= 60:
        return f'<font color="#ffb300"><b>{score}/100 ⚠ Atenção</b></font>'
    else:
        return f'<font color="#ff4444"><b>{score}/100 ✗ Crítico</b></font>'


# ── GERADORES POR MÓDULO ──────────────────────────────────────────────────────

def generate_morphometry_pdf(result: dict) -> bytes:
    elements = []
    s = result.get("stats", {})
    _header(elements, "morphometry", result.get("filename",""), result.get("processing_time_s",0))

    # Métricas principais
    _section(elements, "📊 Estatísticas do Lote")
    metrics = [
        ("Indivíduos",       result.get("count",0),           "#00e5a0"),
        ("Comp. médio (cm)", s.get("length_mean_cm",0),       "#00b4ff"),
        ("Peso médio (g)",   s.get("weight_mean_g",0),        "#ffb300"),
        ("Peso total (g)",   s.get("weight_total_g",0),       "#ff6b6b"),
        ("CV Uniformidade",  f"{s.get('uniformity_cv',0)}%",
            "#00e5a0" if s.get("uniformity_cv",99)<15 else
            "#ffb300" if s.get("uniformity_cv",99)<25 else "#ff4444"),
        ("Escala (px/cm)",   result.get("scale_px_cm",0),     "#7a9abf"),
    ]
    elements.append(_metric_row(metrics))
    elements.append(Spacer(1, 10))

    # Faixa de tamanho
    _section(elements, "📐 Distribuição de Comprimento")
    size_data = [
        ("Menor (cm)", s.get("length_min_cm",0),   "#7a9abf"),
        ("Médio (cm)", s.get("length_mean_cm",0),  "#00e5a0"),
        ("Maior (cm)", s.get("length_max_cm",0),   "#00b4ff"),
        ("Desvio Padrão", s.get("length_std_cm",0),"#ffb300"),
    ]
    elements.append(_metric_row(size_data))
    elements.append(Spacer(1, 10))

    # Imagem anotada
    img = _b64_to_rl_image(result.get("annotated_image",""))
    if img:
        _section(elements, "🖼 Imagem Anotada")
        elements.append(img)
        elements.append(Spacer(1, 8))

    # Tabela individual
    inds = result.get("individuals", [])
    if inds:
        _section(elements, "📋 Dados Individuais")
        headers = ["#", "Comp.(cm)", "Larg.(cm)", "Área(cm²)", "Peso(g)", "Score Saúde", "Alertas"]
        rows = []
        for ind in inds:
            alerts = ", ".join(ind.get("alerts",[])) or "OK"
            rows.append([
                str(ind["id"]),
                str(ind.get("length_cm","")),
                str(ind.get("width_cm","")),
                str(ind.get("area_cm2","")),
                str(ind.get("weight_g","")),
                str(ind.get("health_score","")),
                alerts[:40],
            ])
        elements.append(_data_table(headers, rows))

    # Rodapé
    elements.append(Spacer(1, 16))
    elements.append(HRFlowable(width="100%", thickness=0.3, color=C_MID))
    elements.append(Paragraph(
        "Laudo gerado automaticamente pelo ShrimpScan v2.0 · Pipeline OpenCV · Regressão alometrica P. vannamei",
        ST_SMALL))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=1.5*cm, rightMargin=1.5*cm,
                             topMargin=1.5*cm, bottomMargin=1.5*cm,
                             title="ShrimpScan – Laudo de Morfometria")
    doc.build(elements)
    return buf.getvalue()


def generate_larvae_pdf(result: dict) -> bytes:
    buf = io.BytesIO()
    elements = []
    _header(elements, "larvae", result.get("filename",""), result.get("processing_time_s",0))

    _section(elements, "🔬 Resultado da Análise Larval")
    q = result.get("batch_quality","")
    qcol = {"Excelente":"#00e5a0","Boa":"#00b4ff","Regular":"#ffb300","Baixa":"#ff4444"}.get(q,"#7a9abf")
    metrics = [
        ("Larvas contadas",  result.get("count",0),              "#00e5a0"),
        ("Tam. médio (mm)",  result.get("size_mean_mm",0),       "#00b4ff"),
        ("CV Uniformidade",  f"{result.get('size_cv_pct',0)}%",
            "#00e5a0" if result.get("size_cv_pct",99)<15 else
            "#ffb300" if result.get("size_cv_pct",99)<25 else "#ff4444"),
        ("Estágio",          result.get("stage","—"),            "#ffb300"),
        ("Qualidade lote",   q,                                   qcol),
    ]
    elements.append(_metric_row(metrics))
    elements.append(Spacer(1,10))

    img = _b64_to_rl_image(result.get("annotated_image",""))
    if img:
        _section(elements, "🖼 Imagem Anotada")
        elements.append(img)

    elements.append(Spacer(1, 16))
    elements.append(HRFlowable(width="100%", thickness=0.3, color=C_MID))
    elements.append(Paragraph("ShrimpScan v2.0 · Análise de Larvas / PL", ST_SMALL))

    buf2 = io.BytesIO()
    doc = SimpleDocTemplate(buf2, pagesize=A4,
                             leftMargin=1.5*cm, rightMargin=1.5*cm,
                             topMargin=1.5*cm, bottomMargin=1.5*cm,
                             title="ShrimpScan – Laudo de Larvas")
    doc.build(elements)
    return buf2.getvalue()


def generate_motility_pdf(result: dict) -> bytes:
    elements = []
    _header(elements, "motility", result.get("filename",""), result.get("processing_time_s",0))

    si = result.get("swim_index", 0)
    si_col = ("#00e5a0" if si>=75 else "#00b4ff" if si>=50 else "#ffb300" if si>=25 else "#ff4444")

    _section(elements, "🏊 Índice de Atividade Natatória")
    metrics = [
        ("Índice Natatório",  si,                              si_col),
        ("Classificação",     result.get("swim_class","—"),    si_col),
        ("Duração (s)",       result.get("duration_s",0),      "#7a9abf"),
        ("FPS",               result.get("fps",0),             "#7a9abf"),
        ("Frames analisados", result.get("frames_analyzed",0), "#00b4ff"),
        ("Atividade média",   result.get("activity_mean",0),   "#ffb300"),
        ("Atividade pico",    result.get("activity_max",0),    "#ff6b6b"),
    ]
    elements.append(_metric_row(metrics))
    elements.append(Spacer(1,10))

    # Gráfico de linha da timeline
    timeline = result.get("timeline", [])
    if len(timeline) >= 2:
        _section(elements, "📈 Atividade ao Longo do Tempo")
        d = Drawing(480, 120)
        lp = LinePlot()
        lp.x, lp.y, lp.width, lp.height = 40, 10, 430, 100
        lp.data = [[(p["t_sec"], p["activity"]) for p in timeline]]
        lp.lines[0].strokeColor = C_TEAL
        lp.lines[0].strokeWidth = 1.5
        lp.xValueAxis.valueMin = 0
        lp.xValueAxis.labelTextFormat = "%.0fs"
        lp.xValueAxis.labels.fontSize = 6
        lp.xValueAxis.labels.fillColor = C_GRAY
        lp.yValueAxis.labelTextFormat = "%.2f"
        lp.yValueAxis.labels.fontSize = 6
        lp.yValueAxis.labels.fillColor = C_GRAY
        d.add(lp)
        elements.append(d)
        elements.append(Spacer(1,6))

    # Preview frames
    previews = result.get("preview_frames", [])
    if previews:
        _section(elements, "🎞 Frames com Fluxo Óptico")
        frame_imgs = [_b64_to_rl_image(p, max_w=5.5*cm, max_h=3.5*cm) for p in previews[:6]]
        frame_imgs = [f for f in frame_imgs if f]
        if frame_imgs:
            # 3 por linha
            for i in range(0, len(frame_imgs), 3):
                chunk = frame_imgs[i:i+3]
                while len(chunk) < 3:
                    chunk.append("")
                t = Table([chunk], colWidths=[5.8*cm]*3)
                t.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER"),
                                        ("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
                elements.append(t)
                elements.append(Spacer(1,4))

    elements.append(Spacer(1,16))
    elements.append(HRFlowable(width="100%", thickness=0.3, color=C_MID))
    elements.append(Paragraph("ShrimpScan v2.0 · Optical Flow Farneback (OpenCV)", ST_SMALL))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=1.5*cm, rightMargin=1.5*cm,
                             topMargin=1.5*cm, bottomMargin=1.5*cm,
                             title="ShrimpScan – Laudo de Motilidade")
    doc.build(elements)
    return buf.getvalue()


def generate_health_pdf(result: dict) -> bytes:
    elements = []
    _header(elements, "health", result.get("filename",""), result.get("processing_time_s",0))

    sc = result.get("overall_score", 0)
    sc_col = ("#00e5a0" if sc>=80 else "#ffb300" if sc>=60 else "#ff4444")

    _section(elements, "❤️ Score de Saúde Geral")
    metrics = [
        ("Score Geral",      sc,                              sc_col),
        ("Status",           result.get("status","—"),        sc_col),
        ("Indivíduos",       result.get("count",0),           "#7a9abf"),
    ]
    elements.append(_metric_row(metrics))
    elements.append(Spacer(1,10))

    # Alertas
    alert_sum = result.get("alert_summary", {})
    if alert_sum:
        _section(elements, "⚠️ Alertas Detectados")
        for alert, count in alert_sum.items():
            elements.append(Paragraph(f"• {alert}  ({count}x)", ST_ALERT))
    else:
        _section(elements, "✅ Estado Sanitário")
        elements.append(Paragraph("Nenhum alerta detectado — camarões aparentemente saudáveis.", ST_OK))

    elements.append(Spacer(1,8))
    _section(elements, "ℹ️ Doenças Monitoradas")
    diseases = [
        ("WSSV",          "Manchas brancas (alto V, baixo S no HSV)"),
        ("Black Gill",    "Brânquias escurecidas (baixo V no HSV)"),
        ("Vibriose",      "Coloração avermelhada/alaranjada (H 0–15, S>100)"),
        ("Necrose musc.", "Opacidade muscular (baixo S, V 100–200)"),
    ]
    rows = [[d, desc] for d, desc in diseases]
    elements.append(_data_table(["Doença","Critério de detecção (HSV+Textura)"], rows))
    elements.append(Spacer(1,10))

    # Imagem
    img = _b64_to_rl_image(result.get("annotated_image",""))
    if img:
        _section(elements, "🖼 Imagem Anotada")
        elements.append(img)
        elements.append(Spacer(1,8))

    # Tabela individual
    inds = result.get("individuals", [])
    if inds:
        _section(elements, "📋 Saúde Individual")
        headers = ["#", "Comp.(cm)", "Score", "HSV médio", "Textura Var.", "Alertas"]
        rows = []
        for ind in inds:
            hsv = ind.get("hsv_mean", [])
            hsv_str = "/".join(str(v) for v in hsv) if hsv else "—"
            alerts = ", ".join(ind.get("alerts",[])) or "OK"
            rows.append([
                str(ind["id"]),
                str(ind.get("length_cm","")),
                str(ind.get("health_score","")),
                hsv_str,
                str(ind.get("texture_var","")),
                alerts[:35],
            ])
        elements.append(_data_table(headers, rows))

    elements.append(Spacer(1,16))
    elements.append(HRFlowable(width="100%", thickness=0.3, color=C_MID))
    elements.append(Paragraph("ShrimpScan v2.0 · Análise HSV + Laplacian (OpenCV)", ST_SMALL))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=1.5*cm, rightMargin=1.5*cm,
                             topMargin=1.5*cm, bottomMargin=1.5*cm,
                             title="ShrimpScan – Laudo de Saúde")
    doc.build(elements)
    return buf.getvalue()


def generate_pdf(result: dict) -> bytes:
    """Dispatcher: chama o gerador correto pelo campo 'module'."""
    module = result.get("module", "")
    if module == "morphometry":
        return generate_morphometry_pdf(result)
    elif module == "larvae":
        return generate_larvae_pdf(result)
    elif module == "motility":
        return generate_motility_pdf(result)
    elif module == "health":
        return generate_health_pdf(result)
    else:
        raise ValueError(f"Módulo desconhecido: {module}")
