import argparse
from pathlib import Path

from ultralytics import YOLO


def main() -> None:
    parser = argparse.ArgumentParser(description="Treina YOLO e conta larvas em uma imagem.")
    parser.add_argument("--data", default="dataset_yolo/dataset.yaml", help="Caminho do dataset YAML.")
    parser.add_argument("--source", required=True, help="Imagem para inferencia.")
    parser.add_argument("--epochs", type=int, default=3, help="Epocas de treino rapido.")
    parser.add_argument("--imgsz", type=int, default=640, help="Tamanho de imagem.")
    parser.add_argument("--batch", type=int, default=8, help="Batch size.")
    parser.add_argument("--conf", type=float, default=0.25, help="Threshold de confianca.")
    parser.add_argument("--project", default="runs/shrimp_count", help="Pasta de saida.")
    parser.add_argument("--name", default="quick", help="Nome da execucao.")
    args = parser.parse_args()

    data_path = Path(args.data)
    source_path = Path(args.source)

    if not data_path.exists():
        raise FileNotFoundError(f"Dataset YAML nao encontrado: {data_path}")
    if not source_path.exists():
        raise FileNotFoundError(f"Imagem nao encontrada: {source_path}")

    model = YOLO("yolov8n.pt")

    train_result = model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=0,
        device="cpu",
        project=args.project,
        name=args.name,
        exist_ok=True,
        verbose=False,
    )

    best_model = Path(train_result.save_dir) / "weights" / "best.pt"
    infer_model = YOLO(str(best_model if best_model.exists() else "yolov8n.pt"))

    pred = infer_model.predict(
        source=str(source_path),
        conf=args.conf,
        imgsz=args.imgsz,
        save=True,
        project=args.project,
        name=f"{args.name}_predict",
        exist_ok=True,
        verbose=False,
    )

    boxes = pred[0].boxes
    count = 0 if boxes is None else len(boxes)

    print(f"train_save_dir={train_result.save_dir}")
    print(f"best_model={best_model}")
    print(f"predict_save_dir={Path(args.project) / f'{args.name}_predict'}")
    print(f"count={count}")


if __name__ == "__main__":
    main()
