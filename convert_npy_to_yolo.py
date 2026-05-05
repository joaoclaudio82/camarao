import argparse
import io
import os
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def build_yolo_box(
    x: float,
    y: float,
    sigma: float | None,
    img_w: int,
    img_h: int,
    mode: str,
    fixed_px: float,
    sigma_scale: float,
    min_px: float,
    max_px: float,
) -> tuple[float, float, float, float]:
    if mode == "fixed":
        box_w = fixed_px
        box_h = fixed_px
    else:
        # Quando houver sigma, usamos escala adaptativa.
        raw = (sigma or 0.0) * sigma_scale
        box_w = clamp(raw, min_px, max_px)
        box_h = box_w

    # Centro
    cx = clamp(x, 0.0, img_w - 1.0)
    cy = clamp(y, 0.0, img_h - 1.0)

    # Garantir que a caixa nao vaze a imagem
    half_w = box_w / 2.0
    half_h = box_h / 2.0
    x1 = clamp(cx - half_w, 0.0, img_w - 1.0)
    y1 = clamp(cy - half_h, 0.0, img_h - 1.0)
    x2 = clamp(cx + half_w, 0.0, img_w - 1.0)
    y2 = clamp(cy + half_h, 0.0, img_h - 1.0)

    bw = max(1.0, x2 - x1)
    bh = max(1.0, y2 - y1)
    cx = x1 + bw / 2.0
    cy = y1 + bh / 2.0

    # Normalizacao YOLO
    return (cx / img_w, cy / img_h, bw / img_w, bh / img_h)


def process_split(
    zip_path: Path,
    split_name: str,
    out_root: Path,
    mode: str,
    fixed_px: float,
    sigma_scale: float,
    min_px: float,
    max_px: float,
) -> dict:
    images_out = out_root / split_name / "images"
    labels_out = out_root / split_name / "labels"
    images_out.mkdir(parents=True, exist_ok=True)
    labels_out.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        files = [f for f in zf.namelist() if not f.endswith("/")]
        jpgs = sorted([f for f in files if f.lower().endswith(".jpg")])
        npys = {Path(f).with_suffix("").as_posix(): f for f in files if f.lower().endswith(".npy")}

        converted = 0
        missing_npy = 0
        total_boxes = 0

        for jpg in jpgs:
            stem = Path(jpg).with_suffix("").as_posix()
            npy_file = npys.get(stem)

            img_bytes = zf.read(jpg)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            w, h = img.size

            # Salvar imagem na estrutura YOLO
            image_name = Path(jpg).name
            image_out_path = images_out / image_name
            img.save(image_out_path, format="JPEG", quality=95)

            label_out_path = labels_out / f"{Path(image_name).stem}.txt"

            if not npy_file:
                missing_npy += 1
                label_out_path.write_text("", encoding="utf-8")
                continue

            arr = np.load(io.BytesIO(zf.read(npy_file)), allow_pickle=True)
            if arr.ndim != 2 or arr.shape[1] < 2:
                # formato inesperado, escreve vazio para manter paridade
                label_out_path.write_text("", encoding="utf-8")
                continue

            lines: list[str] = []
            for row in arr:
                x = float(row[0])
                y = float(row[1])
                sigma = float(row[2]) if arr.shape[1] >= 3 else None
                x_n, y_n, w_n, h_n = build_yolo_box(
                    x=x,
                    y=y,
                    sigma=sigma,
                    img_w=w,
                    img_h=h,
                    mode=mode,
                    fixed_px=fixed_px,
                    sigma_scale=sigma_scale,
                    min_px=min_px,
                    max_px=max_px,
                )
                lines.append(f"0 {x_n:.6f} {y_n:.6f} {w_n:.6f} {h_n:.6f}")

            label_out_path.write_text("\n".join(lines), encoding="utf-8")
            converted += 1
            total_boxes += len(lines)

    return {
        "split": split_name,
        "images": len(jpgs),
        "converted": converted,
        "missing_npy": missing_npy,
        "total_boxes": total_boxes,
        "avg_boxes_per_image": round(total_boxes / len(jpgs), 2) if jpgs else 0.0,
    }


def write_dataset_yaml(out_root: Path, yaml_name: str = "dataset.yaml") -> Path:
    yaml_path = out_root / yaml_name
    content = "\n".join(
        [
            f"path: {out_root.as_posix()}",
            "train: train/images",
            "val: test/images",
            "",
            "names:",
            "  0: larva",
            "",
        ]
    )
    yaml_path.write_text(content, encoding="utf-8")
    return yaml_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Converte anotacoes de pontos .npy para labels YOLO (bbox)."
    )
    parser.add_argument("--train-zip", default="shrimp_train.zip", help="Caminho do zip de treino.")
    parser.add_argument("--test-zip", default="shrimp_test.zip", help="Caminho do zip de teste.")
    parser.add_argument(
        "--out-dir",
        default="dataset_yolo",
        help="Pasta de saida no formato YOLO (train/test com images/labels).",
    )
    parser.add_argument(
        "--mode",
        choices=["fixed", "sigma"],
        default="sigma",
        help="fixed: caixa fixa em px | sigma: usa 3a coluna do .npy escalada.",
    )
    parser.add_argument("--fixed-px", type=float, default=16.0, help="Tamanho da caixa no modo fixed.")
    parser.add_argument(
        "--sigma-scale",
        type=float,
        default=0.8,
        help="Fator multiplicador da 3a coluna no modo sigma.",
    )
    parser.add_argument("--min-px", type=float, default=8.0, help="Tamanho minimo da caixa (modo sigma).")
    parser.add_argument("--max-px", type=float, default=36.0, help="Tamanho maximo da caixa (modo sigma).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_zip = Path(args.train_zip)
    test_zip = Path(args.test_zip)
    out_root = Path(args.out_dir)

    if not train_zip.exists():
        raise FileNotFoundError(f"Nao encontrado: {train_zip}")
    if not test_zip.exists():
        raise FileNotFoundError(f"Nao encontrado: {test_zip}")

    out_root.mkdir(parents=True, exist_ok=True)

    train_stats = process_split(
        zip_path=train_zip,
        split_name="train",
        out_root=out_root,
        mode=args.mode,
        fixed_px=args.fixed_px,
        sigma_scale=args.sigma_scale,
        min_px=args.min_px,
        max_px=args.max_px,
    )
    test_stats = process_split(
        zip_path=test_zip,
        split_name="test",
        out_root=out_root,
        mode=args.mode,
        fixed_px=args.fixed_px,
        sigma_scale=args.sigma_scale,
        min_px=args.min_px,
        max_px=args.max_px,
    )
    yaml_path = write_dataset_yaml(out_root)

    for stats in (train_stats, test_stats):
        print(f"\n[{stats['split']}]")
        print(f"images: {stats['images']}")
        print(f"converted: {stats['converted']}")
        print(f"missing_npy: {stats['missing_npy']}")
        print(f"total_boxes: {stats['total_boxes']}")
        print(f"avg_boxes_per_image: {stats['avg_boxes_per_image']}")

    print(f"\nDataset YOLO gerado em: {out_root.resolve()}")
    print(f"YAML: {yaml_path.resolve()}")


if __name__ == "__main__":
    main()
