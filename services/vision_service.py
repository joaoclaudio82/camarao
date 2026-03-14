"""
vision_service.py – Pipeline principal OpenCV para análise de camarões.
Sem dependências de LLM. YOLOv8 é importado somente se disponível.
"""
import cv2
import numpy as np
import io
import base64
import time
from typing import Optional
from PIL import Image

# ─── Tentativa de carregar YOLOv8 (opcional) ─────────────────────────────────
_YOLO_MODEL = None
_YOLO_AVAILABLE = False

def _try_load_yolo():
    global _YOLO_MODEL, _YOLO_AVAILABLE
    if _YOLO_AVAILABLE:
        return True
    try:
        from ultralytics import YOLO
        _YOLO_MODEL = YOLO("yolov8n-seg.pt")
        _YOLO_AVAILABLE = True
        return True
    except Exception:
        _YOLO_AVAILABLE = False
        return False

# ─── Helpers de imagem ────────────────────────────────────────────────────────

def _decode(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Não foi possível decodificar a imagem.")
    return img

def _to_base64(img: np.ndarray, quality: int = 80) -> str:
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()

def _default_scale(img: np.ndarray) -> float:
    """Retorna píxeis por cm – padrão: 60 % da largura = 10 cm (ajuste via calibração)."""
    h, w = img.shape[:2]
    return (w * 0.60) / 10.0   # px/cm

# ─── Segmentação OpenCV (fallback sem YOLOv8) ────────────────────────────────

def _opencv_segment(gray: np.ndarray):
    """Retorna lista de contornos de possíveis camarões.
    Testa THRESH_BINARY e THRESH_BINARY_INV; usa o que gerar mais contornos válidos.
    """
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    h, w = gray.shape
    area_min = (h * w) * 0.002
    area_max = (h * w) * 0.90

    best_cnts, best_thr = [], None
    for flag in (cv2.THRESH_BINARY + cv2.THRESH_OTSU,
                 cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU):
        _, thr = cv2.threshold(blur, 0, 255, flag)
        thr = cv2.morphologyEx(thr, cv2.MORPH_CLOSE, kernel, iterations=3)
        thr = cv2.morphologyEx(thr, cv2.MORPH_OPEN,  kernel, iterations=1)
        cnts, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid = [c for c in cnts if area_min < cv2.contourArea(c) < area_max]
        if len(valid) > len(best_cnts):
            best_cnts, best_thr = valid, thr

    # Fallback: limiar adaptativo
    if not best_cnts:
        thr2 = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY_INV, 21, 4)
        thr2 = cv2.morphologyEx(thr2, cv2.MORPH_CLOSE, kernel, iterations=2)
        cnts2, _ = cv2.findContours(thr2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best_cnts = [c for c in cnts2 if area_min < cv2.contourArea(c) < area_max]
        best_thr  = thr2

    return best_cnts, best_thr if best_thr is not None else np.zeros_like(gray)

# ─── Medidas de contorno ──────────────────────────────────────────────────────

def _contour_measures(cnt, scale_px_cm: float) -> dict:
    """Extrai comprimento, largura, área e peso estimado de um contorno."""
    area_px = cv2.contourArea(cnt)
    if len(cnt) >= 5:
        ellipse = cv2.fitEllipse(cnt)
        major = max(ellipse[1]) / scale_px_cm
        minor = min(ellipse[1]) / scale_px_cm
    else:
        x, y, bw, bh = cv2.boundingRect(cnt)
        major = max(bw, bh) / scale_px_cm
        minor = min(bw, bh) / scale_px_cm
    length_cm = round(major, 2)
    width_cm  = round(minor, 2)
    area_cm2  = round(area_px / (scale_px_cm ** 2), 2)
    # Regressão alométrica P. vannamei: W(g) = 0.000023 * L(mm)^2.87
    length_mm = length_cm * 10
    weight_g  = round(0.000023 * (length_mm ** 2.87), 2)
    return {
        "length_cm": length_cm,
        "width_cm":  width_cm,
        "area_cm2":  area_cm2,
        "weight_g":  weight_g,
    }

# ─── Análise HSV de saúde ─────────────────────────────────────────────────────

def _hsv_health(img_bgr: np.ndarray, cnt) -> dict:
    """Avalia saúde: cor média, textura, manchas melânicas e variância local."""
    mask = np.zeros(img_bgr.shape[:2], np.uint8)
    cv2.drawContours(mask, [cnt], -1, 255, -1)

    body_area = int(np.sum(mask > 0))
    if body_area == 0:
        return {"health_score": 100.0, "hsv_mean": [0, 0, 0], "hsv_std": [0, 0, 0],
                "texture_var": 0.0, "dark_spot_ratio": 0.0, "spot_count": 0, "alerts": []}

    # 1. Estatísticas globais HSV
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mean, std = cv2.meanStdDev(hsv, mask=mask)
    mean_h, mean_s, mean_v = float(mean[0][0]), float(mean[1][0]), float(mean[2][0])
    std_h,  std_s,  std_v  = float(std[0][0]),  float(std[1][0]),  float(std[2][0])

    # 2. Textura (Laplacian variance)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    roi  = cv2.bitwise_and(gray, gray, mask=mask)
    lap  = cv2.Laplacian(roi.astype(np.float32), cv2.CV_32F)
    texture_var = float(np.var(lap[mask > 0]))

    # 3. ─── Detecção de Manchas Melânicas (Dark Spot Detection) ──────────────
    # Estratégia: encontrar pixels ESCUROS (V baixo em HSV) dentro do corpo.
    # Usamos um limiar RELATIVO ao brilho médio para ser robusto a diferentes
    # iluminações e cores de fundo — funciona para manchas pretas em camarão claro
    # ou manchas brancas em camarão escuro.
    v_channel = hsv[:, :, 2]    # canal brilho (Value)
    v_body    = v_channel[mask > 0]

    # Limiar adaptativo: pixels com brilho < q25 - margem são manchas escuras
    q25 = float(np.percentile(v_body, 25))
    dark_threshold = max(20, q25 * 0.55)         # 55% do percentil 25
    _, dark_bin = cv2.threshold(v_channel, dark_threshold, 255, cv2.THRESH_BINARY_INV)
    dark_in_body = cv2.bitwise_and(dark_bin, dark_bin, mask=mask)

    # Morfologia para unir manchas próximas e eliminar ruído de 1–2 px
    kernel  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    dark_in_body = cv2.morphologyEx(dark_in_body, cv2.MORPH_OPEN,  kernel, iterations=1)
    dark_in_body = cv2.morphologyEx(dark_in_body, cv2.MORPH_CLOSE, kernel, iterations=2)

    spot_cnts, _ = cv2.findContours(dark_in_body, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filtro de tamanho RELATIVO: manchas com > 0,15% de área do corpo (escala-invariante)
    min_spot_area = max(10, body_area * 0.0015)
    significant_spots = [c for c in spot_cnts if cv2.contourArea(c) > min_spot_area]

    # Ratio total de área escura dentro do corpo
    dark_pixel_count  = int(np.sum(dark_in_body > 0))
    dark_spot_ratio   = round(dark_pixel_count / body_area * 100, 1)   # %

    # 4. ─── Alertas ─────────────────────────────────────────────────────────
    alerts = []

    # Manchas Melânicas — >3% da área corporal é escura com manchas distintas
    if len(significant_spots) >= 1 and dark_spot_ratio > 3.0:
        severity = "severas" if dark_spot_ratio > 12 else "moderadas" if dark_spot_ratio > 6 else "iniciais"
        alerts.append(
            f"Manchas Melânicas {severity} detectadas "
            f"({len(significant_spots)} focos, {dark_spot_ratio:.1f}% do corpo)"
        )

    # WSSV – corpo muito claro/descolorido + manchas (de outro tipo, brancas)
    if mean_v > 170 and mean_s < 60:
        alerts.append("Possível WSSV (tecido muito descolorido)")

    # Black Gill — globalmente escuro e sem saturação
    if mean_v < 70 and mean_s < 80:
        alerts.append("Possível Black Gill (tecido escurecido)")

    # Vibriose – coloração avermelhada/alaranjada intensa
    if (0 <= mean_h <= 18 or 160 <= mean_h <= 180) and mean_s > 120:
        alerts.append("Sinais de Vibriose (coloração avermelhada anormal)")

    # Necrose muscular / Opacidade — baixa saturação sem ser branco claro ou escuro
    if mean_s < 40 and 90 < mean_v < 175:
        alerts.append("Possível necrose muscular (opacidade tecidual)")

    # Inconsistência de coloração — variância de brilho muito alta
    if std_v > 50:
        alerts.append("Inconsistência de coloração (estresse ou muda incompleta)")

    # Score: base 100, penalizar por cada alerta e pela extensão das manchas
    score = 100.0
    score -= min(len(alerts) * 20, 60)          # -20 por alerta, máx -60
    score -= min(dark_spot_ratio * 1.5, 30)     # -1.5 por % de manchas, máx -30
    if texture_var > 5000:
        score -= 5
    score = max(5.0, round(score, 1))

    return {
        "health_score": score,
        "hsv_mean": [round(mean_h, 1), round(mean_s, 1), round(mean_v, 1)],
        "hsv_std":  [round(std_h, 1),  round(std_s, 1),  round(std_v, 1)],
        "texture_var":    round(texture_var, 1),
        "dark_spot_ratio": dark_spot_ratio,
        "spot_count":    len(significant_spots),
        "alerts":        alerts,
    }

# ─── 1. MORFOMETRIA ───────────────────────────────────────────────────────────

def analyze_morphometry(image_bytes: bytes, filename: str = "") -> dict:
    t0 = time.time()
    img = _decode(image_bytes)
    scale = _default_scale(img)
    gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cnts, thr_img = _opencv_segment(gray)

    individuals = []
    vis = img.copy()
    colors = [(0, 255, 100), (0, 200, 255), (255, 160, 0), (200, 0, 255)]

    for i, cnt in enumerate(cnts[:20]):   # máx 20 indivíduos por imagem
        m = _contour_measures(cnt, scale)
        h = _hsv_health(img, cnt)
        cv2.drawContours(vis, [cnt], -1, colors[i % len(colors)], 2)
        # Label
        M = cv2.moments(cnt)
        if M["m00"] > 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            cv2.putText(vis, f"#{i+1} {m['length_cm']}cm",
                        (cx - 30, cy - 10), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, colors[i % len(colors)], 2)
        individuals.append({"id": i + 1, **m, **h})

    lengths  = [x["length_cm"] for x in individuals]
    weights  = [x["weight_g"]  for x in individuals]
    elapsed  = round(time.time() - t0, 3)

    return {
        "module": "morphometry",
        "filename": filename,
        "count": len(individuals),
        "scale_px_cm": round(scale, 2),
        "method": "opencv_contour",
        "stats": {
            "length_mean_cm": round(np.mean(lengths), 2) if lengths else 0,
            "length_std_cm":  round(np.std(lengths),  2) if lengths else 0,
            "length_min_cm":  round(min(lengths), 2)     if lengths else 0,
            "length_max_cm":  round(max(lengths), 2)     if lengths else 0,
            "weight_mean_g":  round(np.mean(weights), 2) if weights else 0,
            "weight_total_g": round(sum(weights),     2) if weights else 0,
            "uniformity_cv":  round(np.std(lengths) / np.mean(lengths) * 100, 1)
                              if len(lengths) > 1 and np.mean(lengths) > 0 else 0,
        },
        "individuals": individuals,
        "annotated_image": _to_base64(vis),
        "processing_time_s": elapsed,
    }

# ─── 2. ANÁLISE DE LARVAS / PL ────────────────────────────────────────────────

def analyze_larvae(image_bytes: bytes, filename: str = "") -> dict:
    t0 = time.time()
    img  = _decode(image_bytes)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Detecção de blobs (larvas são objetos pequenos)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thr = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    thr = cv2.morphologyEx(thr, cv2.MORPH_OPEN, kernel)
    cnts, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    h_img, w_img = gray.shape
    area_min = 20
    area_max = (h_img * w_img) * 0.05
    valid = [c for c in cnts if area_min < cv2.contourArea(c) < area_max]

    # Escala: assume que a imagem mostra ~5 cm de largura em microscopia
    scale = w_img / 5.0   # px/cm para PL
    sizes_mm = []
    vis = img.copy()

    for cnt in valid[:200]:
        x, y, bw, bh = cv2.boundingRect(cnt)
        size_mm = (max(bw, bh) / scale) * 10
        sizes_mm.append(size_mm)
        cv2.rectangle(vis, (x, y), (x+bw, y+bh), (0, 255, 0), 1)

    count = len(valid)
    mean_sz = round(float(np.mean(sizes_mm)), 2) if sizes_mm else 0
    cv_sz   = round(float(np.std(sizes_mm) / np.mean(sizes_mm) * 100), 1) \
              if len(sizes_mm) > 1 and np.mean(sizes_mm) > 0 else 0

    # Classificação do estágio larval pelo tamanho médio (mm)
    def _stage(sz_mm):
        if sz_mm < 0.3:  return "Náuplio"
        if sz_mm < 0.8:  return "Zoea"
        if sz_mm < 1.5:  return "Mysis"
        if sz_mm < 3.0:  return "PL1–PL5"
        if sz_mm < 6.0:  return "PL6–PL10"
        if sz_mm < 12.0: return "PL11–PL20"
        return "Juvenil"

    stage = _stage(mean_sz)
    quality = "Excelente" if cv_sz < 15 else "Boa" if cv_sz < 25 else "Regular" if cv_sz < 35 else "Baixa"

    return {
        "module": "larvae",
        "filename": filename,
        "count": count,
        "stage": stage,
        "size_mean_mm": mean_sz,
        "size_cv_pct":  cv_sz,
        "batch_quality": quality,
        "annotated_image": _to_base64(vis),
        "processing_time_s": round(time.time() - t0, 3),
    }

# ─── 3. SAÚDE ────────────────────────────────────────────────────────────────

def analyze_health(image_bytes: bytes, filename: str = "") -> dict:
    t0 = time.time()
    img  = _decode(image_bytes)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cnts, _ = _opencv_segment(gray)

    scale = _default_scale(img)
    vis   = img.copy()
    results = []

    for i, cnt in enumerate(cnts[:10]):
        m = _contour_measures(cnt, scale)
        h = _hsv_health(img, cnt)
        color = (0, 200, 0) if not h["alerts"] else (0, 50, 255)
        cv2.drawContours(vis, [cnt], -1, color, 2)
        results.append({"id": i + 1, **h, "length_cm": m["length_cm"]})

    scores = [r["health_score"] for r in results]
    all_alerts = []
    for r in results:
        all_alerts.extend(r["alerts"])
    from collections import Counter
    alert_freq = dict(Counter(all_alerts))

    overall = round(float(np.mean(scores)), 1) if scores else 100.0
    status  = ("Saudável" if overall >= 80
               else "Atenção" if overall >= 60
               else "Crítico")

    return {
        "module": "health",
        "filename": filename,
        "count": len(results),
        "overall_score": overall,
        "status": status,
        "alert_summary": alert_freq,
        "individuals": results,
        "annotated_image": _to_base64(vis),
        "processing_time_s": round(time.time() - t0, 3),
    }

# ─── 4. MOTILIDADE (frame único) ─────────────────────────────────────────────

def analyze_frame(image_bytes: bytes, frame_num: int = 0) -> dict:
    img  = _decode(image_bytes)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cnts, _ = _opencv_segment(gray)
    return {
        "frame": frame_num,
        "count": len(cnts),
    }

# ─── 5. Status do sistema ─────────────────────────────────────────────────────

def check_cv_status() -> dict:
    yolo = _try_load_yolo()
    return {
        "opencv_version": cv2.__version__,
        "numpy_version":  np.__version__,
        "yolo_available": yolo,
        "yolo_model":     "yolov8n-seg.pt" if yolo else None,
        "mode":           "yolo+opencv" if yolo else "opencv_only",
    }
