# 📡 ShrimpScan – Documentação das Rotas da API

**Base URL:** `http://localhost:8000`  
**Docs interativas (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📋 Índice

| Módulo | Método | Rota |
|---|---|---|
| Sistema | GET | `/health` |
| Morfometria | POST | `/api/morphometry/analyze` |
| Morfometria | POST | `/api/morphometry/larvae` |
| Morfometria | GET | `/api/morphometry/history` |
| Motilidade | POST | `/api/motility/analyze` |
| Motilidade | GET | `/api/motility/history` |
| Saúde | POST | `/api/health/analyze` |
| Saúde | GET | `/api/health/history` |
| Calibração | GET | `/api/calibration/references` |
| Calibração | POST | `/api/calibration/auto` |
| Calibração | POST | `/api/calibration/manual` |
| Dashboard | GET | `/api/dashboard/stats` |
| Dashboard | GET | `/api/dashboard/history` |
| Dashboard | DELETE | `/api/dashboard/analysis/{id}` |
| Dashboard | GET | `/api/dashboard/export/csv` |
| Laudos PDF | GET | `/api/reports/analysis/{id}` |
| Laudos PDF | POST | `/api/reports/generate` |

---

## 🩺 Sistema

### `GET /health`

Verifica se o servidor está no ar e retorna a versão dos módulos de visão computacional.

```bash
curl http://localhost:8000/health
```

**Saída:**
```json
{
  "status": "ok",
  "version": "2.1.0",
  "cv_info": {
    "opencv_version": "4.13.0",
    "numpy_version": "2.0.0",
    "yolo_available": true,
    "yolo_model": "yolov8n-seg.pt",
    "mode": "yolo+opencv"
  }
}
```

---

## 📐 Morfometria

### `POST /api/morphometry/analyze`

Analisa uma imagem de camarões adultos: detecta indivíduos, mede comprimento, largura, área e peso estimado, e faz uma pré-avaliação de saúde por cor.

**Parâmetros:** `file` — imagem JPG, PNG ou WEBP (campo `multipart/form-data`)

```bash
curl -X POST http://localhost:8000/api/morphometry/analyze \
  -F "file=@/caminho/para/imagem.jpg"
```

**Saída:**
```json
{
  "module": "morphometry",
  "filename": "imagem.jpg",
  "count": 3,
  "scale_px_cm": 72.0,
  "method": "opencv_contour",
  "stats": {
    "length_mean_cm": 12.4,
    "length_std_cm": 0.8,
    "length_min_cm": 11.5,
    "length_max_cm": 13.2,
    "weight_mean_g": 14.3,
    "weight_total_g": 42.9,
    "uniformity_cv": 6.5
  },
  "individuals": [
    {
      "id": 1,
      "length_cm": 12.4,
      "width_cm": 2.1,
      "area_cm2": 18.5,
      "weight_g": 14.3,
      "health_score": 80.0,
      "hsv_mean": [18.0, 95.0, 145.0],
      "alerts": []
    }
  ],
  "annotated_image": "data:image/jpeg;base64,...",
  "processing_time_s": 0.12
}
```

> **Campos de destaque:**
> - `uniformity_cv`: coeficiente de variação do lote (quanto menor, mais uniforme)
> - `weight_g`: peso estimado via regressão alométrica para *P. vannamei*
> - `annotated_image`: imagem em base64 com contornos desenhados

---

### `POST /api/morphometry/larvae`

Analisa imagens de larvas/PL: contagem por blob detection, tamanho médio, estágio larval e qualidade do lote.

**Parâmetros:** `file` — imagem microscópica JPG, PNG ou WEBP

```bash
curl -X POST http://localhost:8000/api/morphometry/larvae \
  -F "file=@/caminho/para/larvas.jpg"
```

**Saída:**
```json
{
  "module": "larvae",
  "filename": "larvas.jpg",
  "count": 87,
  "stage": "PL6–PL10",
  "size_mean_mm": 7.4,
  "size_cv_pct": 11.2,
  "batch_quality": "Excelente",
  "annotated_image": "data:image/jpeg;base64,...",
  "processing_time_s": 0.08
}
```

> **Estágios reconhecidos:** Náuplio, Zoea, Mysis, PL1–PL5, PL6–PL10, PL11–PL20, Juvenil  
> **Qualidade do lote:** Excelente (CV < 15%), Boa (< 25%), Regular (< 35%), Baixa (≥ 35%)

---

### `GET /api/morphometry/history`

Retorna o histórico de análises de morfometria salvas no banco de dados.

**Parâmetros de query:**
| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `limit` | int | 20 | Número máximo de registros |

```bash
curl "http://localhost:8000/api/morphometry/history?limit=5"
```

**Saída:**
```json
[
  {
    "id": 3,
    "created_at": "2026-03-14T16:00:00",
    "type": "morphometry",
    "filename": "imagem.jpg",
    "summary": { "count": 3, "stats": {...} }
  }
]
```

---

## 🎬 Motilidade

### `POST /api/motility/analyze`

Analisa um vídeo de camarões usando Optical Flow Farneback para calcular o índice natatório (0–100) e gerar uma timeline de atividade.

**Parâmetros:** `file` — vídeo MP4, AVI, MOV, MKV ou WEBM

```bash
curl -X POST http://localhost:8000/api/motility/analyze \
  -F "file=@/caminho/para/video.mp4"
```

**Saída:**
```json
{
  "module": "motility",
  "filename": "video.mp4",
  "swim_index": 72.5,
  "swim_class": "Ativo",
  "total_frames": 300,
  "analyzed_frames": 60,
  "fps": 30.0,
  "duration_s": 10.0,
  "timeline": [
    { "frame": 0, "time_s": 0.0, "flow_mean": 1.2, "active_ratio": 0.85 }
  ],
  "preview_frames": ["data:image/jpeg;base64,..."],
  "processing_time_s": 4.5
}
```

> **Classes de swim_index:** Muito Ativo (≥85), Ativo (≥60), Moderado (≥35), Letárgico (<35)

---

### `GET /api/motility/history`

```bash
curl "http://localhost:8000/api/motility/history?limit=10"
```

Mesma estrutura do histórico de morfometria, com type `"motility"`.

---

## ❤️ Saúde

### `POST /api/health/analyze`

Analisa uma imagem e avalia a saúde dos camarões detectados: manchas melânicas, coloração anormal, Black Gill, Vibriose e necrose muscular.

**Parâmetros:** `file` — imagem JPG, PNG ou WEBP

```bash
curl -X POST http://localhost:8000/api/health/analyze \
  -F "file=@/caminho/para/camarao.jpg"
```

**Saída:**
```json
{
  "module": "health",
  "filename": "camarao.jpg",
  "count": 1,
  "overall_score": 68.0,
  "status": "Atenção",
  "alert_summary": {
    "Manchas Melânicas moderadas detectadas (7 focos, 8.0% do corpo)": 1
  },
  "individuals": [
    {
      "id": 1,
      "health_score": 68.0,
      "hsv_mean": [12.0, 110.0, 145.0],
      "hsv_std": [15.0, 35.0, 55.0],
      "texture_var": 2100.5,
      "dark_spot_ratio": 8.0,
      "spot_count": 7,
      "alerts": [
        "Manchas Melânicas moderadas detectadas (7 focos, 8.0% do corpo)"
      ],
      "length_cm": 13.1
    }
  ],
  "annotated_image": "data:image/jpeg;base64,...",
  "processing_time_s": 0.04
}
```

> **Status:** Saudável (score ≥ 80), Atenção (≥ 60), Crítico (< 60)  
> **dark_spot_ratio:** % da área corporal com manchas escuras — o principal indicador de melanização

**Alertas possíveis:**
| Alerta | Condição |
|---|---|
| Manchas Melânicas iniciais | dark_spot_ratio > 3% |
| Manchas Melânicas moderadas | dark_spot_ratio > 6% |
| Manchas Melânicas severas | dark_spot_ratio > 12% |
| Possível WSSV | corpo muito claro (V > 170, S < 60) |
| Possível Black Gill | tecido globalmente escurecido |
| Vibriose | coloração vermelha/laranja intensa |
| Necrose muscular | opacidade tecidual |
| Inconsistência de coloração | alta variância de brilho (std_v > 50) |

---

### `GET /api/health/history`

```bash
curl "http://localhost:8000/api/health/history?limit=10"
```

---

## 📏 Calibração

### `GET /api/calibration/references`

Lista os tipos de referência suportados para calibração automática.

```bash
curl http://localhost:8000/api/calibration/references
```

**Saída:**
```json
{
  "references": [
    { "key": "R$0,05", "label": "R$0,05", "mm": 17.0 },
    { "key": "R$0,10", "label": "R$0,10", "mm": 20.0 },
    { "key": "R$0,25", "label": "R$0,25", "mm": 25.0 },
    { "key": "R$0,50", "label": "R$0,50", "mm": 23.0 },
    { "key": "R$1,00", "label": "R$1,00", "mm": 27.0 },
    { "key": "R$2,00", "label": "R$2,00", "mm": 28.0 },
    { "key": "régua_1cm", "label": "régua_1cm", "mm": 10.0 },
    { "key": "régua_5cm", "label": "régua_5cm", "mm": 50.0 }
  ]
}
```

---

### `POST /api/calibration/auto`

Detecta automaticamente uma moeda (círculo) ou régua (linha horizontal) na imagem e calcula a escala px/cm.

**Parâmetros de query:**
| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `reference_type` | string | `R$0,25` | Chave da referência (ver `/references`) ou `custom` |
| `custom_mm` | float | — | Tamanho real em mm (apenas quando `reference_type=custom`) |

**Parâmetro de corpo:** `file` — imagem contendo o objeto de referência

```bash
# Com moeda R$0,25
curl -X POST "http://localhost:8000/api/calibration/auto?reference_type=R%240%2C25" \
  -F "file=@/caminho/para/imagem_com_moeda.jpg"

# Com objeto personalizado de 45mm
curl -X POST "http://localhost:8000/api/calibration/auto?reference_type=custom&custom_mm=45" \
  -F "file=@/caminho/para/imagem.jpg"
```

**Saída:**
```json
{
  "status": "ok",
  "reference_type": "R$0,25",
  "reference_mm": 25.0,
  "reference_cm": 2.5,
  "scale_px_cm": 84.32,
  "method": "auto_circle (Hough)",
  "detected_object": {
    "type": "circle",
    "cx": 420, "cy": 310,
    "radius_px": 106,
    "diameter_px": 212
  },
  "image_size": { "width": 1920, "height": 1080 },
  "annotated_image": "data:image/jpeg;base64,..."
}
```

---

### `POST /api/calibration/manual`

Calibração manual: o usuário informa dois pontos na imagem e a distância real entre eles.

**Parâmetros de query (todos obrigatórios):**
| Parâmetro | Tipo | Descrição |
|---|---|---|
| `x1` | int | Coordenada X do ponto 1 (pixels) |
| `y1` | int | Coordenada Y do ponto 1 (pixels) |
| `x2` | int | Coordenada X do ponto 2 (pixels) |
| `y2` | int | Coordenada Y do ponto 2 (pixels) |
| `known_cm` | float | Distância real entre os pontos em cm |

**Parâmetro de corpo:** `file` — imagem

```bash
curl -X POST "http://localhost:8000/api/calibration/manual?x1=100&y1=200&x2=500&y2=200&known_cm=5.0" \
  -F "file=@/caminho/para/imagem.jpg"
```

**Saída:**
```json
{
  "status": "ok",
  "reference_type": "manual_2points",
  "known_cm": 5.0,
  "distance_px": 400.0,
  "scale_px_cm": 80.0,
  "method": "manual_2points",
  "annotated_image": "data:image/jpeg;base64,..."
}
```

---

## 📊 Dashboard

### `GET /api/dashboard/stats`

Retorna totais e gráfico de atividade dos últimos 7 dias.

```bash
curl http://localhost:8000/api/dashboard/stats
```

**Saída:**
```json
{
  "total": 23,
  "by_type": {
    "morphometry": 7,
    "larvae": 4,
    "health": 12
  },
  "recent_7d": [
    { "date": "2026-03-14", "count": 5 }
  ]
}
```

---

### `GET /api/dashboard/history`

Retorna o histórico completo de todas as análises.

**Parâmetros de query:**
| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `limit` | int | 50 | Número máximo de registros |
| `type` | string | — | Filtrar por tipo: `morphometry`, `larvae`, `health`, `motility` |

```bash
# Todos os tipos
curl "http://localhost:8000/api/dashboard/history?limit=20"

# Apenas análises de saúde
curl "http://localhost:8000/api/dashboard/history?type=health&limit=10"
```

**Saída:**
```json
[
  {
    "id": 12,
    "created_at": "2026-03-14T16:00:00",
    "type": "health",
    "filename": "camarao.jpg",
    "summary": {
      "count": 1,
      "overall_score": 68.0,
      "status": "Atenção"
    }
  }
]
```

---

### `DELETE /api/dashboard/analysis/{id}`

Remove uma análise do histórico pelo ID.

```bash
curl -X DELETE http://localhost:8000/api/dashboard/analysis/12
```

**Saída:**
```json
{ "deleted": true, "id": 12 }
```

> Retorna 404 se o ID não existir.

---

### `GET /api/dashboard/export/csv`

Exporta todo o histórico em formato CSV.

```bash
# Imprime no terminal
curl http://localhost:8000/api/dashboard/export/csv

# Salva em arquivo
curl http://localhost:8000/api/dashboard/export/csv -o shrimpscan_export.csv
```

**Saída:** arquivo CSV com colunas `id, created_at, type, filename, summary`.

---

## 📄 Laudos PDF

### `GET /api/reports/analysis/{id}`

Gera e baixa um PDF com o laudo completo de uma análise salva no banco.

```bash
# Baixar PDF da análise #12
curl http://localhost:8000/api/reports/analysis/12 -o laudo_12.pdf
```

> Retorna 404 se o ID não existir, e 500 em caso de erro na geração do PDF.

---

### `POST /api/reports/generate`

Gera um PDF a partir de um payload JSON de resultado (sem precisar salvar no banco).

**Body:** JSON com o resultado completo de uma análise. O campo `"module"` é obrigatório.

```bash
curl -X POST http://localhost:8000/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "module": "health",
    "filename": "camarao.jpg",
    "count": 1,
    "overall_score": 68.0,
    "status": "Atenção",
    "alert_summary": {"Manchas Melânicas moderadas": 1},
    "individuals": []
  }' \
  -o laudo_gerado.pdf
```

---

## 🔗 Fluxo típico no terminal

```bash
# 1. Verificar se o servidor está no ar
curl http://localhost:8000/health

# 2. Calibrar escala usando uma moeda R$0,25
curl -X POST "http://localhost:8000/api/calibration/auto?reference_type=R%240%2C25" \
  -F "file=@foto_com_moeda.jpg"

# 3. Analisar morfometria
curl -X POST http://localhost:8000/api/morphometry/analyze \
  -F "file=@camaroes.jpg"

# 4. Verificar saúde
curl -X POST http://localhost:8000/api/health/analyze \
  -F "file=@camarao_doente.jpg"

# 5. Ver histórico de análises de saúde
curl "http://localhost:8000/api/dashboard/history?type=health&limit=5"

# 6. Baixar laudo PDF do resultado mais recente (substitua o ID)
curl http://localhost:8000/api/reports/analysis/1 -o laudo.pdf

# 7. Exportar tudo em CSV
curl http://localhost:8000/api/dashboard/export/csv -o historico.csv
```
