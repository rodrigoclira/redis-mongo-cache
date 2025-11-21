# Diagramas Visuais - Estratégia de Cache L1

Este documento contém diagramas ASCII para ajudar a visualizar a arquitetura de cache.

## Arquitetura Geral do Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                   APLICAÇÕES CLIENTE                             │
│              (Web, Mobile, Consumidores de API)                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTP/REST API
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DJANGO REST FRAMEWORK                         │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │                    API VIEWS                            │   │
│  │  • FeatureRetrieveView                                 │   │
│  │  • FeatureCreateUpdateView                             │   │
│  │  • FeatureDeleteView                                   │   │
│  │  • BulkFeatureCreateView                               │   │
│  │  • HealthCheckView                                     │   │
│  └────────────────────┬───────────────────────────────────┘   │
│                       │                                         │
│                       ▼                                         │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              SERVIÇO DE FEATURES                        │   │
│  │         (Lógica de Gerenciamento de Cache)              │   │
│  │                                                         │   │
│  │  • get_features()    → Ler com fallback                │   │
│  │  • set_features()    → Escrever em ambas camadas       │   │
│  │  • delete_features() → Remover de ambas                │   │
│  │  • bulk_set_features() → Operações em lote             │   │
│  │  • health_check()    → Monitorar conexões              │   │
│  └────────────────┬──────────────────┬────────────────────┘   │
└───────────────────┼──────────────────┼─────────────────────────┘
                    │                  │
        ┌───────────┘                  └──────────┐
        │                                         │
        ▼                                         ▼
┌──────────────────┐                    ┌──────────────────┐
│   REDIS (L1)     │                    │  MONGODB (L2)    │
│                  │                    │                  │
│  • Em Memória    │                    │  • Baseado em    │
│  • Chave-Valor   │                    │    Disco         │
│  • < 1ms leitura │                    │  • Document DB   │
│  • Suporte TTL   │                    │  • 10-50ms       │
│  • Volátil       │                    │    leitura       │
│                  │                    │  • Persistente   │
│  Porta: 6379     │                    │  • Consultável   │
│                  │                    │                  │
│                  │                    │  Porta: 27017    │
└──────────────────┘                    └──────────────────┘
```

## Diagrama de Fluxo de Leitura (Requisição GET)


```
┌──────────────────────────────────────────────────────────────────┐
│                    REQUISIÇÃO CLIENTE                             │
│           GET /api/features/CUST12345/                           │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
           ┌─────────────────────────┐
           │   Camada View Django    │
           │  FeatureRetrieveView    │
           └────────────┬────────────┘
                        │
                        ▼
           ┌─────────────────────────┐
           │   FeaturesService       │
           │   get_features()        │
           └────────────┬────────────┘
                        │
                        ▼
           ┌─────────────────────────┐
           │  PASSO 1: Verifica Redis│
           │  redis.get(key)         │
           └────────────┬────────────┘
                        │
          ──────────────┴──────────────
         │                             │
         ▼                             ▼
    ┌─────────┐                  ┌──────────┐
    │CACHE HIT│                  │CACHE MISS│
    └────┬────┘                  └────┬─────┘
         │                            │
         │                            ▼
         │              ┌──────────────────────────┐
         │              │ PASSO 2: Consulta MongoDB│
         │              │ mongo.find_one(query)    │
         │              └──────────┬───────────────┘
         │                         │
         │               ──────────┴──────────
         │              │                    │
         │              ▼                    ▼
         │         ┌─────────┐          ┌────────────┐
         │         │ENCONTRADO│          │NÃO ENCONTR.│
         │         └────┬────┘          └───┬────┘
         │              │                   │
         │              ▼                   │
         │    ┌──────────────────────┐     │
         │    │ PASSO 3: Aquece Cache│     │
         │    │ redis.set(key, data) │     │
         │    └──────────┬───────────┘     │
         │               │                  │
         └───────────────┴──────────────────┘
                         │
                         ▼
           ┌─────────────────────────┐
           │   Retorna Resposta JSON │
           │   Status: 200 ou 404    │
           └─────────────────────────┘
                         │
                         ▼
           ┌─────────────────────────┐
           │  Tempos de Resposta:    │
           │   Hit Redis:  < 1ms     │
           │   Hit Mongo:  20-50ms   │
           │   Não Encontrado: 20-50ms│
           └─────────────────────────┘
```

## Diagrama de Fluxo de Escrita (Requisição POST)

```
┌──────────────────────────────────────────────────────────────────┐
│                    REQUISIÇÃO CLIENTE                             │
│          POST /api/features/ + Dados JSON                        │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
           ┌─────────────────────────┐
           │   Camada View Django    │
           │ FeatureCreateUpdateView │
           └────────────┬────────────┘
                        │
                        ▼
           ┌─────────────────────────┐
           │   Valida Requisição     │
           │   CreateFeatureSerializer│
           └────────────┬────────────┘
                        │
                        ▼
           ┌─────────────────────────┐
           │   FeaturesService       │
           │   set_features()        │
           └────────────┬────────────┘
                        │
                        ▼
           ┌─────────────────────────┐
           │  OPERAÇÕES PARALELAS    │
           └────────┬───────┬────────┘
                    │       │
        ┌───────────┘       └───────────┐
        │                               │
        ▼                               ▼
┌───────────────────┐         ┌──────────────────┐
│ PASSO 1: MongoDB  │         │ PASSO 2: Redis   │
│ Salvar em disco   │         │ Cachear em       │
│                   │         │ memória          │
│ Operação:         │         │                  │
│ replace_one()     │         │ Operação:        │
│ com upsert=True   │         │ setex()          │
│                   │         │ com TTL          │
│ Tempo: 10-30ms    │         │                  │
│                   │         │ Tempo: < 1ms     │
└────────┬──────────┘         └────────┬─────────┘
         │                             │
         └──────────────┬──────────────┘
                        │
                        ▼
           ┌─────────────────────────┐
           │   Dados Sincronizados   │
           │   MongoDB: Persistente  │
           │   Redis:   Cache Rápido │
           └────────────┬────────────┘
                        │
                        ▼
           ┌─────────────────────────┐
           │   Retorna Sucesso       │
           │   Status: 201 Criado    │
           │   + Dados de Feature    │
           └─────────────────────────┘
```

## Linha do Tempo Cache Hit vs Cache Miss

```
CENÁRIO 1: CACHE HIT (Redis tem os dados)
════════════════════════════════════════════════════════════════

Tempo (ms)   0         0.5        1         1.5        2
             │          │          │          │          │
Requisição ──┤          │          │          │          │
             │          │          │          │          │
Redis ───────┼──────────┼── Hit    │          │          │
             │          │  (0.5ms) │          │          │
             │          │          │          │          │
Resposta ────┼──────────┼──────────┼─── Enviado │        │
             │          │          │  (1ms)   │          │
MongoDB      │    Não acessado     │          │          │

Total: ~1ms


CENÁRIO 2: CACHE MISS (Redis vazio, MongoDB tem dados)
════════════════════════════════════════════════════════════════

Tempo (ms)   0    5    10   15   20   25   30   35   40   45
             │    │    │    │    │    │    │    │    │    │
Requisição ──┤    │    │    │    │    │    │    │    │    │
             │    │    │    │    │    │    │    │    │    │
Redis ───────┼────┼─ Miss   │    │    │    │    │    │    │
             │    │ (0.5ms) │    │    │    │    │    │    │
             │    │    │    │    │    │    │    │    │    │
MongoDB ─────┼────┼────┼────┼────┼─ Hit     │    │    │    │
             │    │    │    │    │ (20ms)   │    │    │    │
             │    │    │    │    │    │    │    │    │    │
Aquece Redis ┼────┼────┼────┼────┼────┼─Set │    │    │    │
             │    │    │    │    │    │(1ms)│    │    │    │
             │    │    │    │    │    │    │    │    │    │
Resposta ────┼────┼────┼────┼────┼────┼────┼─ Enviado│    │
             │    │    │    │    │    │    │ (22ms)  │    │

Total: ~22ms (mas próxima requisição será ~1ms)
```

## Estrutura de Dados no Armazenamento

```
┌─────────────────────────────────────────────────────────────────┐
│                          REDIS (L1)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Padrão de Chave: "features:{customer_id}"                      │
│                                                                  │
│  Exemplo:                                                        │
│    Chave: "features:CUST12345"                                  │
│    TTL: 604800 segundos (7 dias)                                │
│    Valor: {                                                      │
│      "customer_id": "CUST12345",                                │
│      "features": {                                              │
│        "payment_history_score": 0.85,                           │
│        "credit_utilization": 0.30,                              │
│        "account_age_months": 36                                 │
│      },                                                          │
│      "calculated_at": "2025-11-20T10:00:00Z",                   │
│      "model_version": "v1.0.0",                                 │
│      "expires_at": "2025-11-27T10:00:00Z"                       │
│    }                                                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         MONGODB (L2)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Coleção: "customer_features"                                   │
│  Banco de Dados: "cache_demo"                                   │
│                                                                  │
│  Exemplo de Documento:                                          │
│  {                                                               │
│    "_id": ObjectId("..."),                                      │
│    "customer_id": "CUST12345",      ← Indexado (único)         │
│    "features": {                                                │
│      "payment_history_score": 0.85,                             │
│      "credit_utilization": 0.30,                                │
│      "account_age_months": 36                                   │
│    },                                                            │
│    "calculated_at": "2025-11-20T10:00:00Z",                     │
│    "model_version": "v1.0.0",                                   │
│    "expires_at": ISODate("2025-11-27T10:00:00Z") ← Índice TTL  │
│  }                                                               │
│                                                                  │
│  Índices:                                                        │
│    • customer_id (único)                                        │
│    • expires_at (índice TTL, auto-delete)                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Gráfico de Comparação de Performance

## Gráfico de Comparação de Performance

```
Comparação de Tempo de Resposta
═══════════════════════════════════════════════════════════════

Origem          Tempo de Resposta    Visual
──────────────────────────────────────────────────────────────

Redis (L1)      < 1ms           ▓
                                │
MongoDB (L2)    10-50ms         ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
                                │
Sem Cache       50-200ms        ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
                                │
                    0ms     25ms     50ms     75ms     100ms    125ms    150ms


Comparação de Throughput (requisições/segundo)
═══════════════════════════════════════════════════════════════

Configuração    Throughput      Visual
──────────────────────────────────────────────────────────────

Redis (L1)      10.000+        ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
                                │
Apenas MongoDB  200-500        ▓▓▓
                                │
                        0      2k     4k     6k     8k     10k
```

## Taxa de Acerto de Cache ao Longo do Tempo

```
Evolução da Taxa de Acerto de Cache
═══════════════════════════════════════════════════════════════

100% │                    ╭─────────────────────────────
     │                  ╱
     │                ╱
 75% │              ╱
     │            ╱
     │          ╱
 50% │        ╱
     │      ╱
     │    ╱
 25% │  ╱
     │╱
   0% └────────────────────────────────────────────────────►
      Cold    Aquecendo   Cache      Cache     Estado
      Start              Quente     Muito Q.  Estável

Linha do Tempo:
  • Cold Start (0%):      Sistema iniciado, cache vazio
  • Aquecendo (25-50%):   Requisições iniciais populando cache
  • Cache Quente (75-90%):Dados mais comuns em cache
  • Cache Muito Quente (90-95%): Performance ótima
  • Estado Estável (95%+):Sistema maduro com padrões
```

## Mapa de Serviços Docker Compose

```
┌─────────────────────────────────────────────────────────────────┐
│                    STACK DOCKER COMPOSE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────┐         ┌──────────────┐                    │
│   │   Redis      │         │   MongoDB    │                    │
│   │              │         │              │                    │
│   │  Porta: 6379 │         │ Porta: 27017 │                    │
│   │  Imagem: 7.2 │         │ Imagem: 7.0  │                    │
│   │              │         │              │                    │
│   │ Volume:      │         │ Volume:      │                    │
│   │  redis_data  │         │ mongodb_data │                    │
│   └───────▲──────┘         └──────▲───────┘                    │
│           │                       │                             │
│           │                       │                             │
│           └───────────┬───────────┘                             │
│                       │                                         │
│                       │                                         │
│                ┌──────▼───────┐                                │
│                │   Django     │                                │
│                │   Web App    │                                │
│                │              │                                │
│                │  Porta: 8000 │◄──────── Acesso Externo        │
│                │              │                                │
│                │ Imagem:      │                                │
│                │   Python 3.11│                                │
│                └──────────────┘                                │
│                                                                  │
│   Rede: cache-network (bridge)                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

Health Checks:
  Redis:   A cada 10s → redis-cli PING
  MongoDB: A cada 10s → comando ping mongosh
  Web:     Depende da saúde do Redis & MongoDB
```

---

Estes diagramas ajudam a visualizar a arquitetura e fluxo de dados da estratégia de cache L1.
Para exploração interativa, use o Swagger UI em http://localhost:8000/swagger/
