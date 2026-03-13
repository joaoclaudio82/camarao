# camarao-ia

Repositório do serviço de IA do sistema Camarão. Processa imagens e vídeos usando inteligência artificial, consumindo eventos do SQS e devolvendo resultados ao backend.

## Stack

| Tecnologia | Uso |
|------------|-----|
| **AWS SQS** | Consumo de eventos (filas) |
| **Amazon S3** | Leitura dos arquivos a processar |
| **Backend API** | Envio dos resultados do processamento |

## Responsabilidades

- Consumo de mensagens do SQS quando lotes estão prontos
- Recuperação de imagens e vídeos no S3
- Processamento com modelos de IA
- Envio dos resultados para a API do backend

## Integração

O serviço opera **desacoplado**: o backend publica no SQS e a IA consome de forma assíncrona, permitindo escalabilidade e resiliência.

## Fluxo no Sistema

1. Backend publica mensagem no SQS
2. IA consome a mensagem
3. Recupera arquivos do lote no S3
4. Processa imagens e vídeos
5. Envia resultado para a API do backend
6. Backend atualiza status e disponibiliza para o frontend

## Repositórios relacionados

- [camarao-backend](https://github.com/IFCE/camarao-backend)
- [camarao-frontend](https://github.com/IFCE/camarao-frontend)
- [camarao-mobile](https://github.com/IFCE/camarao-mobile)
