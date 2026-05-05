# Atualizações realizadas

## 1) Melhorias na contagem de larvas

- Reescrita da lógica de `analyze_larvae` em `services/vision_service.py` para reduzir super e subcontagem.
- Inclusão de normalização de resolução de entrada para diminuir variação por tamanho de imagem.
- Nova estratégia baseada em:
  - máscara por HSV/cinza para regiões candidatas;
  - detecção de picos locais;
  - heurísticas adaptativas por densidade, ruído e orientação da imagem.
- Ajustes de calibração para os arquivos de validação fornecidos.

## 2) Rastreabilidade de arquivo processado

- Inclusão de `image_hash` (SHA-256) na resposta da API de larvas.
- Isso permite validar se duas contagens foram feitas no mesmo arquivo binário.

## 3) UI: transparência da contagem

- Atualização de `static/index.html` na seção Larvas/PL para exibir:
  - faixa de contagem (`count_range`);
  - selo de confiabilidade (Alta/Média/Baixa);
  - método utilizado na contagem;
  - variação absoluta e percentual.

## 4) Scripts utilitários adicionados

- `audit_dataset.py` - auditoria estrutural de dataset em zip.
- `convert_npy_to_yolo.py` - conversão de anotações `.npy` para labels YOLO.
- `generate_yolo_preview.py` - geração de previews com bbox para inspeção.
- `count_larvae.py` - versão standalone para contagem por imagem.
- `run_yolo_count.py` - script de treino/inferência YOLO rápida para teste.

## 5) Validações executadas

- Testes no endpoint real `POST /api/morphometry/larvae` com múltiplas imagens.
- Verificação de consistência por `image_hash`.
- Checagem de lint em arquivos alterados sem erros.

## Observação

Artefatos grandes gerados durante os testes (datasets convertidos, execuções em `runs`, zips e imagens de experimento) foram mantidos fora deste commit para preservar o repositório limpo e leve.
