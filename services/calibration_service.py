"""
calibration_service.py – Calibração de escala px/cm por referência visual.
Suporta: régua (linha reta detectada), moeda (círculo), ou dimensão manual.
"""
import cv2
import numpy as np
import base64
from typing import Optional, Tuple

# Diâmetros de moedas em mm (referências comuns no Brasil)
COIN_DIAMETERS_MM = {
    "R$0,05": 17.0,
    "R$0,10": 20.0,
    "R$0,25": 25.0,
    "R$0,50": 23.0,
    "R$1,00": 27.0,
    "R$2,00": 28.0,
    "régua_1cm": 10.0,
    "régua_5cm": 50.0,
}


def _to_b64(img: np.ndarray) -> str:
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()


def calibrate_with_reference(
    image_bytes: bytes,
    reference_type: str = "R$0,25",
    custom_mm: Optional[float] = None,
) -> dict:
    """
    Detecta automaticamente um objeto de referência na imagem e calcula px/cm.

    Args:
        image_bytes:    bytes da imagem
        reference_type: chave em COIN_DIAMETERS_MM ou 'custom'
        custom_mm:      tamanho real em mm (apenas se reference_type='custom')

    Returns:
        dict com scale_px_cm, method, annotated_image, ...
    """
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return {"error": "Não foi possível decodificar a imagem."}

    vis = img.copy()
    h, w = img.shape[:2]

    # Tamanho real de referência
    if reference_type == "custom" and custom_mm:
        ref_mm = custom_mm
    else:
        ref_mm = COIN_DIAMETERS_MM.get(reference_type, 25.0)
    ref_cm = ref_mm / 10.0

    # ── Tenta detecção automática de círculo (moeda) ──────────────────────────
    gray   = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur   = cv2.GaussianBlur(gray, (9, 9), 2)
    circles = cv2.HoughCircles(
        blur, cv2.HOUGH_GRADIENT, dp=1.2,
        minDist=int(min(h, w) * 0.15),
        param1=60, param2=35,
        minRadius=int(min(h, w) * 0.04),
        maxRadius=int(min(h, w) * 0.40),
    )

    scale_px_cm: Optional[float] = None
    method = "manual"
    detected_obj = None

    if circles is not None:
        # Usa o círculo mais próximo ao centro
        circs = np.uint16(np.around(circles[0]))
        cx_img, cy_img = w // 2, h // 2
        best = min(circs, key=lambda c: (int(c[0])-cx_img)**2 + (int(c[1])-cy_img)**2)
        cx, cy, cr = int(best[0]), int(best[1]), int(best[2])
        diameter_px = cr * 2
        scale_px_cm = diameter_px / ref_cm
        method = f"auto_circle (Hough)"
        detected_obj = {"type": "circle", "cx": cx, "cy": cy, "radius_px": cr,
                        "diameter_px": diameter_px}
        # Desenha
        cv2.circle(vis, (cx, cy), cr, (0, 229, 160), 3)
        cv2.circle(vis, (cx, cy), 4,  (0, 229, 160), -1)
        cv2.putText(vis, f"{ref_mm:.0f}mm ref ({scale_px_cm:.1f}px/cm)",
                    (cx - 60, cy + cr + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 229, 160), 2)
    else:
        # ── Tenta detecção de linha horizontal (régua) ────────────────────────
        edges = cv2.Canny(blur, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=80,
                                minLineLength=int(w * 0.15), maxLineGap=20)
        if lines is not None:
            # Seleciona a linha mais longa e horizontal
            best_line = None
            best_len  = 0
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = abs(np.degrees(np.arctan2(y2-y1, x2-x1)))
                length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
                if angle < 15 and length > best_len:
                    best_len  = length
                    best_line = (x1, y1, x2, y2)
            if best_line:
                x1, y1, x2, y2 = best_line
                length_px = np.sqrt((x2-x1)**2 + (y2-y1)**2)
                scale_px_cm = length_px / ref_cm
                method = "auto_line (Hough)"
                detected_obj = {"type":"line", "x1":x1,"y1":y1,"x2":x2,"y2":y2,
                                 "length_px": round(float(length_px),1)}
                cv2.line(vis, (x1,y1),(x2,y2), (0,180,255), 3)
                cv2.putText(vis, f"{ref_mm:.0f}mm ref ({scale_px_cm:.1f}px/cm)",
                            (x1, y1-12), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,180,255), 2)

    # ── Fallback: usa largura da imagem como referência ───────────────────────
    if scale_px_cm is None:
        scale_px_cm = w / 20.0   # assume 20 cm de largura
        method = "fallback_image_width"
        cv2.putText(vis, f"Escala padrão: {scale_px_cm:.1f} px/cm",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 179, 0), 2)

    return {
        "status": "ok",
        "reference_type": reference_type,
        "reference_mm": ref_mm,
        "reference_cm": ref_cm,
        "scale_px_cm": round(float(scale_px_cm), 2),
        "method": method,
        "detected_object": detected_obj,
        "image_size": {"width": w, "height": h},
        "annotated_image": _to_b64(vis),
    }


def calibrate_manual(image_bytes: bytes,
                     point1: Tuple[int,int],
                     point2: Tuple[int,int],
                     known_cm: float) -> dict:
    """
    Calibração manual: usuário clica em dois pontos e informa a distância real.
    """
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return {"error": "Imagem inválida."}

    vis = img.copy()
    dx = point2[0] - point1[0]
    dy = point2[1] - point1[1]
    dist_px = float(np.sqrt(dx**2 + dy**2))
    scale_px_cm = dist_px / known_cm

    cv2.line(vis, point1, point2, (0, 229, 160), 3)
    cv2.circle(vis, point1, 6, (0, 229, 160), -1)
    cv2.circle(vis, point2, 6, (0, 229, 160), -1)
    mid = ((point1[0]+point2[0])//2, (point1[1]+point2[1])//2)
    cv2.putText(vis, f"{known_cm}cm = {dist_px:.0f}px → {scale_px_cm:.2f}px/cm",
                (mid[0]-80, mid[1]-12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 229, 160), 2)

    return {
        "status": "ok",
        "reference_type": "manual_2points",
        "known_cm": known_cm,
        "distance_px": round(dist_px, 1),
        "scale_px_cm": round(scale_px_cm, 2),
        "method": "manual_2points",
        "annotated_image": _to_b64(vis),
    }
