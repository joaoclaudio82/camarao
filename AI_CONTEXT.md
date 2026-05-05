# AI Context - ShrimpScan

## Objetivo do projeto

O `ShrimpScan` e uma aplicacao web/API para analise de camaroes por visao computacional, focada em aquicultura.
Ele processa imagens e videos para gerar metricas de:

- morfometria;
- larvas/PL;
- motilidade;
- saude;
- calibracao de escala;
- historico e laudos.

Nao depende de LLM para funcionar em producao.

## Stack e componentes principais

- `FastAPI` para API HTTP.
- `OpenCV + NumPy` para pipeline de visao computacional.
- `SQLite` para persistencia do historico (`data/shrimpscan.db`).
- `ReportLab` para geracao de laudos PDF.
- Frontend estatico em `static/index.html` (HTML + JS + Tailwind + Chart.js via CDN).

## Estrutura do codigo

- `app.py`: inicializacao da API, CORS, montagem dos routers e rota raiz.
- `routers/`: definicao dos endpoints por modulo.
  - `morphometry.py`
  - `motility.py`
  - `health.py`
  - `calibration.py`
  - `dashboard.py`
  - `reports.py`
- `services/`: regra de negocio e processamento.
  - `vision_service.py`: morfometria, larvas, saude.
  - `video_service.py`: motilidade por optical flow.
  - `calibration_service.py`: calibracao automatica/manual.
  - `db_service.py`: persistencia e consultas.
  - `pdf_service.py`: montagem de laudos.

## Endpoints principais

### Sistema
- `GET /health`: status do servidor e info do OpenCV/YOLO.

### Morfometria
- `POST /api/morphometry/analyze`
- `POST /api/morphometry/larvae`
- `GET /api/morphometry/history`

### Motilidade
- `POST /api/motility/analyze`
- `GET /api/motility/history`

### Saude
- `POST /api/health/analyze`
- `GET /api/health/history`

### Calibracao
- `GET /api/calibration/references`
- `POST /api/calibration/auto`
- `POST /api/calibration/manual`

### Dashboard
- `GET /api/dashboard/stats`
- `GET /api/dashboard/history`
- `DELETE /api/dashboard/analysis/{id}`
- `GET /api/dashboard/export/csv`

### Laudos PDF
- `GET /api/reports/analysis/{id}`
- `POST /api/reports/generate`

## Como a analise funciona (visao geral)

1. Usuario envia imagem/video.
2. Router valida tipo de arquivo.
3. Service processa com OpenCV.
4. Resultado e retornado como JSON.
5. Parte do resultado e salva em SQLite (sem blobs grandes como imagens base64).
6. Dashboard e historico consomem os dados persistidos.
7. PDF pode ser gerado via ID salvo ou payload direto.

## Convencoes observadas no projeto

- Codigo e comentarios majoritariamente em portugues.
- Respostas de API com estrutura direta, campos explicitos por modulo.
- Campos de visualizacao (`annotated_image`, `preview_frames`) retornam base64.
- Historico no banco salva resumo e resultado limpo para reduzir tamanho.

## Pontos de atencao tecnicos

- A calibracao no frontend aparenta manter estado local (`_savedScale`), mas a morfometria no backend usa escala padrao interna (`_default_scale`) quando nao recebe calibracao externa.
- YOLO e opcional; o caminho principal de segmentacao atual e OpenCV.
- `created_at` usa `datetime.utcnow()` sem timezone explicito no banco.

## Setup rapido local

```bash
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

- App web: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

## Checklist para IA antes de alterar codigo

- Ler `README.md` e `rotas.md`.
- Validar impacto em router + service + persistencia.
- Conferir se mudancas de payload quebram frontend (`static/index.html`).
- Manter compatibilidade com historico salvo no SQLite.
- Se alterar calculos, atualizar texto/rotas/documentacao.

## Diretriz para futuras iteracoes

Quando iniciar uma tarefa no projeto:

1. identificar modulo alvo (morfometria, larvas, motilidade, saude, calibracao, dashboard, relatorios);
2. mapear endpoint -> service -> persistencia;
3. definir se a mudanca impacta API, frontend e PDF;
4. validar resposta JSON final e campos esperados pelo frontend;
5. registrar ajuste relevante no README ou neste arquivo.
