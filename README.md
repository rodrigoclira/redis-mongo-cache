# Estratégia de Cache L1 com Redis e MongoDB

Um projeto Django Rest Framework demonstrando uma arquitetura de cache de duas camadas usando Redis como cache L1 (Nível 1) e MongoDB como armazenamento persistente L2.

## Visão Geral do Projeto

Este projeto demonstra uma estratégia eficiente de cache onde:
- **Redis** atua como cache L1 para recuperação de dados ultra-rápida (< 1ms)
- **MongoDB** serve como camada de armazenamento persistente L2 (10-50ms)
- Aquecimento automático de cache e expiração baseada em TTL

## Arquitetura

```
┌─────────────┐
│   Cliente   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│    Django REST API          │
│  (Camada de Lógica)         │
└──────┬──────────────────────┘
       │
       ▼
┌──────────────────────┐
│  FeaturesService     │
│  (Gerenciador Cache) │
└─────┬───────────┬────┘
      │           │
      ▼           ▼
┌──────────┐  ┌──────────┐
│  Redis   │  │ MongoDB  │
│  (L1)    │  │  (L2)    │
│  Cache   │  │Armazenam.│
└──────────┘  └──────────┘
```

## Fluxo de Cache

### Operação de Leitura
1. Client requests data for `customer_id`
2. System checks **Redis** (L1 cache) first
3. **Cache HIT** → Return data immediately
4. **Cache MISS** → Query **MongoDB** (L2)
5. If found in MongoDB → Update Redis cache + Return data
6. If not found → Return 404

### Write Operation
1. Client sends data to create/update
2. System writes to **MongoDB** (persistent)
3. System caches in **Redis** with TTL
4. Return success response

## Getting Started

### Prerequisites

- Python 3.10+
- Docker & Docker Compose (for containerized setup)
- Redis 7.x
- MongoDB 7.x

### Installation

#### Opção 1: Usando Docker (Recomendado)

```bash
# Clone o repositório
git clone <repository-url>
cd redis-mongo-cache

# Inicie todos os serviços
docker-compose up -d

# Verifique a saúde dos serviços
docker-compose ps
```

A API estará disponível em: `http://localhost:8000`

#### Opção 2: Desenvolvimento Local

```bash
# Crie o ambiente virtual
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt

# Copie o arquivo de ambiente
cp .env.example .env

# Inicie Redis e MongoDB (usando Docker)
docker-compose up -d redis mongodb

# Execute as migrações
python manage.py migrate

# Inicie o servidor de desenvolvimento
python manage.py runserver
```

## Documentação da API

### Documentação Interativa
- **Swagger UI**: http://localhost:8000/swagger/
- **ReDoc**: http://localhost:8000/redoc/

### Endpoints Principais

#### 1. Obter Informações da Estratégia de Cache
```bash
GET /api/info/
```
Retorna informações detalhadas sobre a implementação da estratégia de cache L1.

#### 2. Verificação de Saúde
```bash
GET /api/health/
```
Verifica o status das conexões Redis e MongoDB.

#### 3. Recuperar Features (Demonstra Estratégia de Cache)
```bash
GET /api/features/{customer_id}/
```
Demonstra o padrão de busca de cache L1 → L2.

#### 4. Criar/Atualizar Features
```bash
POST /api/features/
Content-Type: application/json

{
  "customer_id": "CUST12345",
  "features": {
    "payment_history_score": 0.85,
    "credit_utilization": 0.30,
    "account_age_months": 36
  },
  "model_version": "v1.0.0",
  "ttl_days": 7
}
```

#### 5. Deletar Features
```bash
DELETE /api/features/{customer_id}/delete/
```

#### 6. Criar/Atualizar em Lote
```bash
POST /api/features/bulk/
Content-Type: application/json

{
  "features_list": [
    {
      "customer_id": "CUST001",
      "features": {"score": 0.85}
    },
    {
      "customer_id": "CUST002",
      "features": {"score": 0.92}
    }
  ],
  "model_version": "v1.0.0",
  "ttl_days": 7
}
```

## Testando a Estratégia de Cache

### Exemplo de Fluxo de Trabalho

```bash
# 1. Create a feature
curl -X POST http://localhost:8000/api/features/ \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST12345",
    "features": {
      "payment_history_score": 0.85,
      "credit_utilization": 0.30
    }
  }'

# 2. Retrieve feature (will hit Redis cache)
curl http://localhost:8000/api/features/CUST12345/

# 3. Check logs to see "Features cache HIT for CUST12345 (Redis)"

# 4. Delete from Redis only (to test MongoDB fallback)
docker exec cache-demo-redis redis-cli DEL "features:CUST12345"

# 5. Retrieve again (will hit MongoDB, then warm Redis)
curl http://localhost:8000/api/features/CUST12345/

# 6. Check logs to see "Features cache MISS Redis, HIT MongoDB"
```

## Principais Benefícios

### Redis (Cache L1)
- **Ultra-rápido**: Acesso em memória (< 1ms)
- **Expiração automática**: Limpeza baseada em TTL
- **Carga reduzida**: Minimiza consultas ao MongoDB
- **Alto throughput**: Lida com leituras frequentes eficientemente

### MongoDB (Armazenamento L2)
- **Persistente**: Dados sobrevivem a reinicializações
- **Consultável**: Consultas complexas e indexação
- **Fonte da verdade**: Armazenamento autoritativo de dados
- **Índices TTL**: Expiração automática de documentos

## Características de Performance

| Operação | Redis (L1) | MongoDB (L2) |
|----------|-----------|--------------|
| Leitura | < 1ms | 10-50ms |
| Escrita | < 1ms | 10-50ms |
| Taxa de Cache Hit | 80-95% | N/A |
| Durabilidade | Volátil* | Persistente |

*Redis pode ser configurado para persistência com AOF (Append Only File)

## Configuração

### Variáveis de Ambiente

```bash
# Configurações Django
SECRET_KEY=sua-chave-secreta
DEBUG=True

# Configurações Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_TTL=604800  # 7 dias em segundos

# Configurações MongoDB
MONGO_URI=mongodb://localhost:27017/
MONGO_DB=cache_demo
```

## Estrutura do Projeto

```
redis-mongo-cache/
├── api/
│   ├── services.py          # FeaturesService (cache manager)
│   ├── views.py             # API views
│   ├── serializers.py       # DRF serializers
│   └── urls.py              # API routes
├── cache_project/
│   ├── settings.py          # Django settings
│   └── urls.py              # Main URL configuration
├── docker-compose.yml       # Docker services
├── Dockerfile               # Django app container
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Tecnologias Utilizadas

- **Django 4.2**: Framework web
- **Django REST Framework 3.14**: Framework de API
- **Redis 7.2**: Cache em memória
- **MongoDB 7.0**: Banco de dados NoSQL
- **drf-yasg**: Documentação Swagger/OpenAPI
- **Docker**: Containerização

## Casos de Uso

Esta estratégia de cache é ideal para:
- Features/scores pré-calculados
- Dados acessados frequentemente
- Predições de modelos de ML
- Perfis de clientes
- Resultados de busca
- Dados de sessão

## Contribuindo

Sinta-se à vontade para enviar issues e solicitações de melhorias!

## Licença

MIT License
