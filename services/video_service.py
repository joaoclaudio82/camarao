"""
video_service.py – Análise de motilidade por vídeo (Optical Flow Farneback).
"""
import cv2
import numpy as np
import tempfile
import os
import time
import base64
from typing import List

def _flow_activity(flow: np.ndarray) -> float:
    """Retorna magnitude média do fluxo óptico."""
    mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    return float(np.mean(mag))

def _to_base64_frame(frame: np.ndarray) -> str:
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    if not ok:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()

def analyze_video(video_bytes: bytes, filename: str = "") -> dict:
    t0 = time.time()
    # Salva temporariamente
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    try:
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            return {"error": "Não foi possível abrir o vídeo.", "module": "motility"}

        fps_vid   = cap.get(cv2.CAP_PROP_FPS) or 25
        total_frm = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration  = round(total_frm / fps_vid, 1) if fps_vid > 0 else 0

        activities: List[float] = []
        frame_data:  List[dict] = []
        preview_frames = []

        ret, prev = cap.read()
        if not ret:
            return {"error": "Vídeo vazio ou corrompido.", "module": "motility"}

        prev_gray = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
        frame_idx = 0
        sample_every = max(1, int(fps_vid / 5))   # 5 amostras/segundo

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1
            if frame_idx % sample_every != 0:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, gray,
                None, 0.5, 3, 15, 3, 5, 1.2, 0
            )
            activity = _flow_activity(flow)
            activities.append(activity)

            t_sec = round(frame_idx / fps_vid, 2)
            frame_data.append({"t_sec": t_sec, "activity": round(activity, 4)})

            # Visualização: desenha vetores de fluxo a cada 16 px
            vis = frame.copy()
            step = 16
            h, w = gray.shape
            for y in range(0, h, step):
                for x in range(0, w, step):
                    fx, fy = flow[y, x]
                    mag = np.sqrt(fx**2 + fy**2)
                    if mag > 1.0:
                        x2 = int(x + fx * 2)
                        y2 = int(y + fy * 2)
                        cv2.arrowedLine(vis, (x, y), (x2, y2),
                                        (0, 255, 120), 1, tipLength=0.3)

            prev_gray = gray
            # Guarda até 6 frames de preview
            if len(preview_frames) < 6:
                preview_frames.append(_to_base64_frame(vis))

        cap.release()

        if not activities:
            return {"error": "Sem frames processados.", "module": "motility"}

        act_arr  = np.array(activities)
        mean_act = float(np.mean(act_arr))
        max_act  = float(np.max(act_arr))

        # Índice de atividade natatória (0–100)
        # Normalizado: média/3 * 100 (calibrar com dados reais)
        swim_index = min(100, round(mean_act / 3.0 * 100, 1))

        # Classificação
        if swim_index >= 75:
            swim_class = "Alta atividade (Excelente)"
        elif swim_index >= 50:
            swim_class = "Atividade moderada (Boa)"
        elif swim_index >= 25:
            swim_class = "Baixa atividade (Atenção)"
        else:
            swim_class = "Inatividade (Crítico)"

        return {
            "module": "motility",
            "filename": filename,
            "duration_s": duration,
            "total_frames": total_frm,
            "fps": round(fps_vid, 1),
            "frames_analyzed": len(activities),
            "swim_index": swim_index,
            "swim_class": swim_class,
            "activity_mean": round(mean_act, 4),
            "activity_max":  round(max_act,  4),
            "timeline": frame_data,
            "preview_frames": preview_frames,
            "processing_time_s": round(time.time() - t0, 3),
        }
    finally:
        os.unlink(tmp_path)
