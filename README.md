# ShrimpScan v2.0 – Análise Inteligente de Camarões

## Visão Geral
Aplicação web para análise de imagens e vídeos de camarões.
**Sem dependências de LLM** — usa apenas OpenCV + NumPy + FastAPI.

## Módulos
| Módulo | Método | Saída |
|---|---|---|
| Morfometria | Segmentação OpenCV + fitEllipse | Comprimento, largura, área, peso (regressão alométrica) |
| Larvas / PL | Blob detection | Contagem, tamanho médio, uniformidade, estágio, qualidade do lote |
| Motilidade | Optical Flow Farneback | Índice natatório 0–100, timeline, preview frames |
| Saúde | HSV + Laplacian | Score 0–100, alertas WSSV / Black Gill / Vibriose / Necrose |
| Dashboard | SQLite | Histórico, gráficos, export CSV |

## Requisitos
- Python 3.10+
- Dependências: `pip install -r requirements.txt`
- **Não requer** GPU, API key, Ollama ou conexão com internet

## Instalação e execução

```bash
git clone <repo> shrimpscan
cd shrimpscan
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Acesse: http://localhost:8000

## Estrutura
```
shrimpscan/
├── app.py                   # FastAPI principal
├── requirements.txt
├── .env.example
├── routers/
│   ├── morphometry.py       # POST /api/morphometry/analyze, /larvae
│   ├── motility.py          # POST /api/motility/analyze
│   ├── health.py            # POST /api/health/analyze
│   └── dashboard.py         # GET /api/dashboard/stats, history, export
├── services/
│   ├── vision_service.py    # Pipeline OpenCV (morfometria, larvas, saúde)
│   ├── video_service.py     # Optical Flow Farneback
│   └── db_service.py        # SQLite
├── static/
│   └── index.html           # SPA – dark glassmorphism UI
├── data/                    # shrimpscan.db (auto-gerado)
└── uploads/                 # temporário
```

## YOLOv8 (opcional)
Para segmentação mais precisa, instale o módulo opcional:
```bash
pip install ultralytics torch torchvision --index-url https://download.pytorch.org/whl/cpu
```
O sistema detecta automaticamente e usa YOLOv8n-seg quando disponível.

## API Endpoints
- `POST /api/morphometry/analyze` – imagem → medidas
- `POST /api/morphometry/larvae`  – imagem larvas → contagem/uniformidade
- `POST /api/motility/analyze`    – vídeo → índice natatório
- `POST /api/health/analyze`      – imagem → score de saúde
- `GET  /api/dashboard/stats`     – totais e gráficos
- `GET  /api/dashboard/history`   – histórico completo
- `GET  /api/dashboard/export/csv`– export CSV
- `GET  /docs`                    – Swagger UI automático
