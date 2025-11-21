# Resumo do Projeto - Demonstração da Estratégia de Cache L1

## Estrutura do Projeto

```
redis-mongo-cache/
├── api/                              # App Django para a REST API
│   ├── management/
│   │   └── commands/
│   │       └── populate_sample_data.py  # Comando para gerar dados de teste
│   ├── services.py                  # FeaturesService (gerenciador de cache)
│   ├── views.py                     # Endpoints da API (views DRF)
│   ├── serializers.py               # Serializadores DRF
│   └── urls.py                      # Roteamento de URLs da API
├── cache_project/                    # Configuração do projeto Django
│   ├── settings.py                  # Configurações Django (Redis/MongoDB)
│   └── urls.py                      # Configuração principal de URLs + Swagger
├── docker-compose.yml               # Serviços Docker (Redis, MongoDB, Django)
├── Dockerfile                       # Definição do container da aplicação Django
├── requirements.txt                 # Dependências Python
├── manage.py                        # Script de gerenciamento Django
├── quickstart.sh                    # Script de configuração com um comando
├── .env.example                     # Template de variáveis de ambiente
├── .gitignore                       # Regras de ignore do Git
├── README.md                        # Documentação principal do projeto
├── TESTING.md                       # Guia de testes com exemplos
└── CACHE_STRATEGY.md                # Análise profunda da estratégia de cache
```

## Principais Recursos Implementados

### 1. **Serviço de Cache L1** (`api/services.py`)
- Classe `FeaturesService` que gerencia Redis e MongoDB
- Fallback automático de Redis → MongoDB
- Aquecimento de cache em acertos do MongoDB
- Expiração baseada em TTL
- Suporte a operações em lote
- Monitoramento de saúde

### 2. **Endpoints da REST API** (`api/views.py`)
- `GET /api/features/{customer_id}/` - Recuperar features (demonstra fluxo de cache)
- `POST /api/features/` - Criar/atualizar features
- `DELETE /api/features/{customer_id}/delete/` - Deletar features
- `POST /api/features/bulk/` - Criar/atualizar em lote
- `GET /api/health/` - Verificação de saúde para Redis e MongoDB
- `GET /api/info/` - Informações da estratégia de cache

### 3. **Documentação da API**
- Swagger UI em `/swagger/`
- ReDoc em `/redoc/`
- Interface de testes interativa

### 4. **Configuração Docker**
- Redis 7.2 (cache L1)
- MongoDB 7.0 (armazenamento L2)
- Container da aplicação Django
- Todos os serviços com verificações de saúde

### 5. **Comandos de Gerenciamento**
- `populate_sample_data` - Gerar clientes de teste

## Início Rápido

### Opção 1: Usando o Script de Início Rápido (Mais Fácil)

```bash
./quickstart.sh
```

Este script irá:
1. Verificar instalação do Docker
2. Criar arquivo .env
3. Iniciar todos os serviços
4. Executar migrações
5. Criar dados de exemplo
6. Exibir URLs de acesso

### Opção 2: Configuração Manual

```bash
# 1. Iniciar serviços
docker-compose up -d

# 2. Executar migrações
docker-compose exec web python manage.py migrate

# 3. Criar dados de exemplo
docker-compose exec web python manage.py populate_sample_data --count 10

# 4. Acessar a API
open http://localhost:8000/swagger/
```

### Opção 3: Desenvolvimento Local (sem Docker para o Django)

```bash
# 1. Iniciar Redis e MongoDB
docker-compose up -d redis mongodb

# 2. Instalar dependências Python
pip install -r requirements.txt

# 3. Executar migrações
python manage.py migrate

# 4. Iniciar servidor Django
python manage.py runserver

# 5. Acessar a API
open http://localhost:8000/swagger/
```

## Testando a Estratégia de Cache

### Teste Rápido

```bash
# 1. Verificação de saúde
curl http://localhost:8000/api/health/

# 2. Criar uma feature
curl -X POST http://localhost:8000/api/features/ \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "TEST001", "features": {"score": 0.85}}'

# 3. Recuperar feature (Cache HIT no Redis)
curl http://localhost:8000/api/features/TEST001/

# 4. Limpar cache Redis
docker exec cache-demo-redis redis-cli DEL "features:TEST001"

# 5. Recuperar novamente (Fallback MongoDB → Aquecimento Redis)
curl http://localhost:8000/api/features/TEST001/
```

Veja `TESTING.md` para cenários abrangentes de teste.

## Fluxo da Estratégia de Cache

```
┌─────────────────────────────────────────────────────┐
│                 REQUISIÇÃO DE LEITURA                │
│            GET /api/features/CUST12345/             │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  Verificar Redis (L1)  │
        └────────┬───────────────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
   [CACHE HIT]       [CACHE MISS]
        │                 │
        │                 ▼
        │    ┌────────────────────────┐
        │    │  Consultar MongoDB (L2)│
        │    └────────┬───────────────┘
        │             │
        │    ┌────────┴────────┐
        │    │                 │
        │    ▼                 ▼
        │ [ENCONTRADO]     [NÃO ENCONTRADO]
        │    │                 │
        │    ├─► Atualizar Redis│
        │    │                 │
        ▼    ▼                 ▼
   Retornar Dados       Retornar 404
   (< 1ms)              (20-50ms)
```

## Objetivos de Aprendizado

Ao explorar este projeto, você entenderá:

1. **Padrão de Cache L1**: Como implementar uma estratégia de cache de duas camadas
2. **Uso do Redis**: Cache em memória com TTL
3. **Integração MongoDB**: Armazenamento persistente de documentos
4. **Django REST Framework**: Construção de REST APIs
5. **Aquecimento de Cache**: População automática de cache
6. **Monitoramento de Saúde**: Verificações de saúde de serviços
7. **Docker Compose**: Orquestração multi-container
8. **Documentação de API**: Integração Swagger/OpenAPI

## Benefícios de Performance

| Métrica | Sem Cache | Com Cache L1 | Melhoria |
|--------|--------------|---------------|-------------|
| Tempo de Resposta | 20-50ms | < 1ms | **20-50x mais rápido** |
| Carga no Banco de Dados | 100% | 5-20% | **Redução de 80-95%** |
| Requisições/seg | ~200 | ~10,000+ | **Aumento de 50x** |
| Custo | Alto | Baixo | **Economia significativa** |

## Configuração

### Variáveis de Ambiente (`.env`)

```bash
# Django
SECRET_KEY=sua-chave-secreta
DEBUG=True

# Redis (Cache L1)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_TTL=604800  # 7 dias

# MongoDB (Armazenamento L2)
MONGO_URI=mongodb://localhost:27017/
MONGO_DB=cache_demo
```

### Personalizando TTL

Em `cache_project/settings.py`:
```python
REDIS_TTL = 3600  # 1 hora
REDIS_TTL = 86400  # 1 dia
REDIS_TTL = 604800  # 7 dias (padrão)
```

## Arquivos de Documentação

- **README.md** - Visão geral do projeto e configuração
- **CACHE_STRATEGY.md** - Análise técnica profunda dos padrões de cache
- **TESTING.md** - Guia de testes passo a passo
- **Este arquivo** - Resumo do projeto e referência rápida

## Tecnologias

| Tecnologia | Versão | Propósito |
|------------|---------|---------|
| Python | 3.10+ | Linguagem de programação |
| Django | 4.2.7 | Framework web |
| Django REST Framework | 3.14.0 | Framework de REST API |
| Redis | 7.2 | Cache L1 em memória |
| MongoDB | 7.0 | Armazenamento L2 persistente |
| drf-yasg | 1.21.7 | Documentação da API |
| Docker | Latest | Containerização |

## Casos de Uso

Esta arquitetura é perfeita para:

- **Feature Stores de ML**: Features pré-calculadas para modelos
- **E-commerce**: Catálogos de produtos, precificação
- **Perfis de Usuário**: Dados de usuário acessados frequentemente
- **Analytics**: Métricas de dashboard, relatórios
- **Sessões**: Estado de autenticação de usuário
- **APIs Mobile**: Acesso a dados de baixa latência

## Solução de Problemas

### Serviços não iniciam
```bash
docker-compose down
docker-compose up -d
docker-compose logs
```

### Não consegue conectar ao Redis/MongoDB
```bash
# Verificar se os serviços estão rodando
docker-compose ps

# Testar conexão Redis
docker exec cache-demo-redis redis-cli PING

# Testar conexão MongoDB
docker exec -it cache-demo-mongodb mongosh --eval "db.version()"
```

### Erros de importação
```bash
# Reconstruir containers
docker-compose build --no-cache
docker-compose up -d
```

## Indicadores de Sucesso

Você saberá que o projeto está funcionando quando:

- Todos os containers estão rodando (`docker-compose ps` mostra "Up")  
- Verificação de saúde retorna status 200 com ambos os serviços saudáveis  
- Swagger UI carrega em http://localhost:8000/swagger/  
- Dados de exemplo são criados com sucesso  
- Primeira busca registra "MongoDB HIT", segunda busca registra "Redis HIT"  
- Tempo de resposta para dados em cache < 5ms  

## Próximos Passos

Para estender este projeto:

1. **Adicionar Autenticação**: Tokens JWT com armazenamento de sessão Redis
2. **Implementar Rate Limiting**: Usando contadores Redis
3. **Adicionar Métricas**: Dashboard Prometheus + Grafana
4. **Teste de Carga**: Apache Bench ou Locust
5. **Invalidação de Cache**: Padrão pub/sub com Redis
6. **Read Replicas**: Replica set MongoDB para escalonamento
7. **Redis Cluster**: Sharding para escalonamento horizontal
8. **Pipeline CI/CD**: GitHub Actions para testes automatizados

## Suporte

- Abra uma issue para bugs
- Verifique `TESTING.md` para cenários comuns
- Leia `CACHE_STRATEGY.md` para detalhes de arquitetura
- Revise a documentação da API em `/swagger/` para uso dos endpoints

---

**Feito para demonstrar padrões de cache L1 com Redis e MongoDB**
