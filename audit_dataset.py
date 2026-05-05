import os
import zipfile
from collections import Counter, defaultdict

ZIP_FILES = ["shrimp_train.zip", "shrimp_test.zip"]
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
LABEL_EXT = ".txt"


def base_no_ext(path: str) -> str:
    return os.path.splitext(path)[0]


def is_image(path: str) -> bool:
    return os.path.splitext(path.lower())[1] in IMAGE_EXTS


def is_label(path: str) -> bool:
    return path.lower().endswith(LABEL_EXT)


def audit_zip(zip_path: str) -> None:
    print(f"\n=== Auditando: {zip_path} ===")
    if not os.path.exists(zip_path):
        print("Arquivo nao encontrado.")
        return

    with zipfile.ZipFile(zip_path, "r") as zf:
        files = [f for f in zf.namelist() if not f.endswith("/")]
        images = [f for f in files if is_image(f)]
        labels = [f for f in files if is_label(f)]

        image_bases = {base_no_ext(f) for f in images}
        label_bases = {base_no_ext(f) for f in labels}

        missing_label = sorted(image_bases - label_bases)
        orphan_label = sorted(label_bases - image_bases)

        print(f"Total arquivos: {len(files)}")
        print(f"Imagens: {len(images)}")
        print(f"Labels .txt: {len(labels)}")
        print(f"Imagens sem label: {len(missing_label)}")
        print(f"Labels sem imagem: {len(orphan_label)}")

        invalid_labels = []
        class_counter = Counter()
        lines_error = defaultdict(list)

        for lbl in labels:
            try:
                raw = zf.read(lbl).decode("utf-8", errors="replace").strip().splitlines()
            except Exception as e:
                invalid_labels.append((lbl, f"erro leitura: {e}"))
                continue

            if len(raw) == 0:
                invalid_labels.append((lbl, "arquivo vazio"))
                continue

            ok_file = True
            for i, line in enumerate(raw, 1):
                parts = line.strip().split()
                if len(parts) != 5:
                    ok_file = False
                    lines_error[lbl].append(f"linha {i}: esperado 5 campos, veio {len(parts)}")
                    continue

                cls, x, y, w, h = parts
                try:
                    cls_id = int(cls)
                    x = float(x)
                    y = float(y)
                    w = float(w)
                    h = float(h)
                except ValueError:
                    ok_file = False
                    lines_error[lbl].append(f"linha {i}: valores nao numericos")
                    continue

                class_counter[cls_id] += 1

                if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1):
                    ok_file = False
                    lines_error[lbl].append(
                        f"linha {i}: bbox fora do intervalo [0,1] ou w/h <= 0"
                    )

            if not ok_file:
                invalid_labels.append((lbl, "formato/conteudo invalido"))

        print(f"Labels invalidos: {len(invalid_labels)}")
        print(f"Classes encontradas: {dict(class_counter)}")

        if missing_label:
            print("\nExemplos de imagens sem label:")
            for item in missing_label[:10]:
                print(" -", item)

        if orphan_label:
            print("\nExemplos de labels sem imagem:")
            for item in orphan_label[:10]:
                print(" -", item)

        if invalid_labels:
            print("\nExemplos de labels invalidos:")
            for lbl, reason in invalid_labels[:10]:
                print(f" - {lbl}: {reason}")
                for err in lines_error.get(lbl, [])[:3]:
                    print(f"    * {err}")


if __name__ == "__main__":
    for zip_file in ZIP_FILES:
        audit_zip(zip_file)
