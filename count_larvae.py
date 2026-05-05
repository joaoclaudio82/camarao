import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi


def count_components_for_threshold(
    roi_gray: np.ndarray,
    threshold: int,
    area_min: int,
    area_max: int,
    open_iterations: int,
):
    # Segmenta pixels escuros (pontos de larva) em fundo claro
    mask = roi_gray < threshold

    # Para este dataset, os alvos sao pontos pequenos; abertura excessiva remove sinal.
    # Mantemos opcional para casos com muito ruido.
    if open_iterations > 0:
        structure = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool)
        mask = ndi.binary_opening(mask, structure=structure, iterations=open_iterations)

    labels, n = ndi.label(mask)
    if n == 0:
        return 0, [], mask

    objects = ndi.find_objects(labels)
    areas = np.bincount(labels.ravel())[1:]  # ignora label 0 (fundo)

    kept_boxes = []
    for i, slc in enumerate(objects, start=1):
        if slc is None:
            continue
        area = int(areas[i - 1])
        if area < area_min or area > area_max:
            continue
        y1, y2 = slc[0].start, slc[0].stop
        x1, x2 = slc[1].start, slc[1].stop
        kept_boxes.append((x1, y1, x2, y2, area))

    return len(kept_boxes), kept_boxes, mask


def robust_count(
    roi_gray: np.ndarray,
    area_min: int,
    area_max: int,
    t_start: int,
    t_end: int,
    t_step: int,
    open_iterations: int,
):
    results = []
    for t in range(t_start, t_end + 1, t_step):
        count, boxes, _ = count_components_for_threshold(
            roi_gray=roi_gray,
            threshold=t,
            area_min=area_min,
            area_max=area_max,
            open_iterations=open_iterations,
        )
        results.append({"threshold": t, "count": count, "boxes": boxes})

    counts = np.array([r["count"] for r in results], dtype=np.int32)
    median_count = int(np.median(counts))

    # Escolhe o threshold cuja contagem fica mais proxima da mediana
    best = min(results, key=lambda r: abs(r["count"] - median_count))
    return best, results


def draw_debug(
    image_rgb: Image.Image,
    boxes,
    roi_y1: int,
    output_path: Path,
    final_count: int,
    threshold: int,
):
    dbg = image_rgb.copy()
    draw = ImageDraw.Draw(dbg)

    for (x1, y1, x2, y2, _area) in boxes:
        draw.rectangle((x1, y1 + roi_y1, x2, y2 + roi_y1), outline=(0, 210, 0), width=1)

    draw.rectangle((10, 10, 340, 52), fill=(0, 0, 0))
    draw.text((16, 18), f"count={final_count}  th={threshold}", fill=(255, 255, 255))

    dbg.save(output_path, format="JPEG", quality=95)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Conta larvas por pontos escuros (threshold + connected components)."
    )
    parser.add_argument("--image", required=True, help="Caminho da imagem de entrada.")
    parser.add_argument(
        "--out-image",
        default="larvae_debug.jpg",
        help="Caminho da imagem de debug com caixas desenhadas.",
    )
    parser.add_argument(
        "--out-json",
        default="larvae_count.json",
        help="Caminho para salvar o resumo da contagem em JSON.",
    )
    parser.add_argument("--roi-top", type=float, default=0.12, help="Corte superior da ROI (0-1).")
    parser.add_argument("--roi-bottom", type=float, default=0.80, help="Corte inferior da ROI (0-1).")
    parser.add_argument("--area-min", type=int, default=1, help="Area minima de componente.")
    parser.add_argument("--area-max", type=int, default=200, help="Area maxima de componente.")
    parser.add_argument("--t-start", type=int, default=120, help="Threshold inicial.")
    parser.add_argument("--t-end", type=int, default=140, help="Threshold final.")
    parser.add_argument("--t-step", type=int, default=2, help="Passo do threshold.")
    parser.add_argument(
        "--open-iterations",
        type=int,
        default=0,
        help="Iteracoes de abertura morfologica (0 desabilita).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    image_path = Path(args.image)
    out_image_path = Path(args.out_image)
    out_json_path = Path(args.out_json)

    if not image_path.exists():
        raise FileNotFoundError(f"Imagem nao encontrada: {image_path}")

    img_rgb = Image.open(image_path).convert("RGB")
    gray = np.array(img_rgb.convert("L"))
    h, _w = gray.shape

    roi_y1 = int(h * args.roi_top)
    roi_y2 = int(h * args.roi_bottom)
    roi_gray = gray[roi_y1:roi_y2, :]

    best, all_results = robust_count(
        roi_gray=roi_gray,
        area_min=args.area_min,
        area_max=args.area_max,
        t_start=args.t_start,
        t_end=args.t_end,
        t_step=args.t_step,
        open_iterations=args.open_iterations,
    )

    final_count = int(best["count"])
    threshold = int(best["threshold"])
    boxes = best["boxes"]
    counts = [int(r["count"]) for r in all_results]

    draw_debug(
        image_rgb=img_rgb,
        boxes=boxes,
        roi_y1=roi_y1,
        output_path=out_image_path,
        final_count=final_count,
        threshold=threshold,
    )

    payload = {
        "image": str(image_path),
        "count": final_count,
        "threshold_selected": threshold,
        "count_range": {"min": int(min(counts)), "max": int(max(counts))},
        "threshold_sweep": [
            {"threshold": int(r["threshold"]), "count": int(r["count"])} for r in all_results
        ],
        "params": {
            "roi_top": args.roi_top,
            "roi_bottom": args.roi_bottom,
            "area_min": args.area_min,
            "area_max": args.area_max,
            "t_start": args.t_start,
            "t_end": args.t_end,
            "t_step": args.t_step,
            "open_iterations": args.open_iterations,
        },
        "debug_image": str(out_image_path),
    }

    out_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
