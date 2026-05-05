import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw


def parse_label_line(line: str):
    parts = line.strip().split()
    if len(parts) != 5:
        return None
    cls_id, x, y, w, h = parts
    return int(cls_id), float(x), float(y), float(w), float(h)


def draw_boxes(image_path: Path, label_path: Path, out_path: Path) -> int:
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    img_w, img_h = image.size

    count = 0
    if label_path.exists():
        for raw_line in label_path.read_text(encoding="utf-8").splitlines():
            parsed = parse_label_line(raw_line)
            if not parsed:
                continue
            _, x, y, w, h = parsed
            cx = x * img_w
            cy = y * img_h
            bw = w * img_w
            bh = h * img_h
            x1 = max(0, int(cx - bw / 2))
            y1 = max(0, int(cy - bh / 2))
            x2 = min(img_w - 1, int(cx + bw / 2))
            y2 = min(img_h - 1, int(cy + bh / 2))
            draw.rectangle((x1, y1, x2, y2), outline=(255, 64, 64), width=1)
            count += 1

    image.save(out_path, format="JPEG", quality=92)
    return count


def generate_preview(split_dir: Path, out_dir: Path, sample_size: int, seed: int) -> None:
    images_dir = split_dir / "images"
    labels_dir = split_dir / "labels"
    split_name = split_dir.name

    image_files = sorted(images_dir.glob("*.jpg"))
    if not image_files:
        print(f"[{split_name}] nenhuma imagem encontrada.")
        return

    rnd = random.Random(seed)
    selected = image_files if sample_size >= len(image_files) else rnd.sample(image_files, sample_size)

    split_out = out_dir / split_name
    split_out.mkdir(parents=True, exist_ok=True)

    print(f"\n[{split_name}] gerando {len(selected)} previews...")
    for image_path in selected:
        label_path = labels_dir / f"{image_path.stem}.txt"
        out_path = split_out / f"{image_path.stem}_preview.jpg"
        boxes = draw_boxes(image_path, label_path, out_path)
        print(f"- {image_path.name}: {boxes} boxes")


def main():
    parser = argparse.ArgumentParser(description="Gera preview visual dos labels YOLO.")
    parser.add_argument("--dataset-dir", default="dataset_yolo", help="Raiz do dataset YOLO.")
    parser.add_argument("--out-dir", default="dataset_yolo_preview", help="Pasta de saida dos previews.")
    parser.add_argument("--sample-train", type=int, default=8, help="Quantidade de previews de treino.")
    parser.add_argument("--sample-test", type=int, default=8, help="Quantidade de previews de teste.")
    parser.add_argument("--seed", type=int, default=42, help="Seed para amostragem.")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    out_dir = Path(args.out_dir)

    generate_preview(dataset_dir / "train", out_dir, args.sample_train, args.seed)
    generate_preview(dataset_dir / "test", out_dir, args.sample_test, args.seed + 1)
    print(f"\nPreviews salvos em: {out_dir.resolve()}")


if __name__ == "__main__":
    main()
