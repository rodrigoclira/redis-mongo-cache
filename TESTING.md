# Guia de Testes - Demonstração da Estratégia de Cache L1

Este guia orienta você através dos testes da estratégia de cache L1 com Redis e MongoDB.

## Pré-requisitos

Certifique-se de que todos os serviços estão rodando:
```bash
docker-compose up -d
```

Verifique a saúde dos serviços:
```bash
docker-compose ps
```

> Caso esteja executando pela primeira vez, popule o banco usando o script `quickstart.sh`. 

## Cenários de Teste

### 1. Testar Verificação de Saúde

```bash
curl http://localhost:8000/api/health/ | jq
```

Resposta esperada:
```json
{
  "redis": {
    "available": true,
    "status": "healthy",
    "total_keys": 0,
    "used_memory": "1.23M"
  },
  "mongodb": {
    "available": true,
    "status": "healthy",
    "documents_count": 0,
    "collection": "customer_features"
  }
}
```

### 2. Obter Informações da Estratégia de Cache

```bash
curl http://localhost:8000/api/info/ | jq
```

Isso retorna informações detalhadas sobre a implementação da estratégia de cache.

### 3. Criar uma Feature (Escrever em Redis e MongoDB)

```bash
curl -X POST http://localhost:8000/api/features/ \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST12345",
    "features": {
      "payment_history_score": 0.85,
      "credit_utilization": 0.30,
      "account_age_months": 36,
      "recent_inquiries": 2,
      "debt_to_income": 0.35
    },
    "model_version": "v1.0.0",
    "ttl_days": 7
  }' | jq
```

### 4. Recuperar Feature - Testar Cache HIT (Redis)

```bash
curl http://localhost:8000/api/features/CUST12345/ | jq
```

**Verifique os logs do Django** para ver:

```bash
docker-compose logs | egrep "CUST12345"
```

```
INFO Features cache HIT for CUST12345 (Redis)
```

### 5. Testar Cache MISS e Fallback do MongoDB

**Passo 1:** Deletar a chave apenas do Redis (não do MongoDB)
```bash
docker exec cache-demo-redis redis-cli DEL "features:CUST12345"
```

**Passo 2:** Recuperar a feature novamente
```bash
curl http://localhost:8000/api/features/CUST12345/ | jq
```

**Verifique os logs do Django** para ver:
```
INFO Features cache MISS Redis, HIT MongoDB for CUST12345
INFO Features cached in Redis for CUST12345
```

Isso demonstra o padrão de fallback L1 → L2!

### 6. Testar MISS Completo (Não está nem no Redis nem no MongoDB)

```bash
curl http://localhost:8000/api/features/NONEXISTENT/ | jq
```

Resposta esperada (404):
```json
{
  "error": "Features not found for customer_id: NONEXISTENT"
}
```

### 7. Criar Features em Lote

```bash
curl -X POST http://localhost:8000/api/features/bulk/ \
  -H "Content-Type: application/json" \
  -d '{
    "features_list": [
      {
        "customer_id": "CUST001",
        "features": {
          "payment_history_score": 0.92,
          "credit_utilization": 0.25
        }
      },
      {
        "customer_id": "CUST002",
        "features": {
          "payment_history_score": 0.78,
          "credit_utilization": 0.45
        }
      },
      {
        "customer_id": "CUST003",
        "features": {
          "payment_history_score": 0.88,
          "credit_utilization": 0.32
        }
      }
    ],
    "model_version": "v1.0.0",
    "ttl_days": 7
  }' | jq
```

Resposta esperada:
```json
{
  "success": 3,
  "failed": 0,
  "message": "Bulk operation completed"
}
```

### 8. Deletar uma Feature

```bash
curl -X DELETE http://localhost:8000/api/features/CUST12345/delete/
```

Isso remove a feature tanto do Redis quanto do MongoDB.

## Testes de Performance

### Testar Performance do Redis

Recupere a mesma feature múltiplas vezes e observe o tempo de resposta:

```bash
# Primeira chamada (pode vir do MongoDB se não estiver em cache)
time curl http://localhost:8000/api/features/CUST001/

# Chamadas subsequentes (do cache Redis - devem ser mais rápidas)
time curl http://localhost:8000/api/features/CUST001/
time curl http://localhost:8000/api/features/CUST001/
```

### Monitorar Chaves do Redis

```bash
# Listar todas as chaves de features
docker exec cache-demo-redis redis-cli KEYS "features:*"

# Obter uma chave específica
docker exec cache-demo-redis redis-cli GET "features:CUST001"

# Verificar TTL de uma chave
docker exec cache-demo-redis redis-cli TTL "features:CUST001"
```

### Monitorar MongoDB

```bash
# Conectar ao MongoDB
docker exec -it cache-demo-mongodb mongosh cache_demo

# Listar todos os documentos
db.customer_features.find().pretty()

# Contar documentos
db.customer_features.countDocuments()

# Encontrar documento específico
db.customer_features.findOne({customer_id: "CUST001"})

# Sair do shell do MongoDB
exit
```

## Usando o Gerador de Dados de Exemplo

Popule 20 clientes de exemplo:

```bash
python manage.py populate_sample_data --count 20
```

Então teste a recuperação:
```bash
curl http://localhost:8000/api/features/CUST00001/ | jq
curl http://localhost:8000/api/features/CUST00010/ | jq
```

## Documentação Interativa da API

Visite essas URLs no seu navegador:

- **Swagger UI**: http://localhost:8000/swagger/
  - Documentação interativa da API
  - Teste os endpoints diretamente do navegador
  
- **ReDoc**: http://localhost:8000/redoc/
  - Documentação limpa e legível

## Monitorando Taxa de Acertos do Cache

Para monitorar a efetividade do cache:

1. Crie múltiplas features
2. Consulte-as repetidamente
3. Verifique estatísticas do Redis:

```bash
docker exec cache-demo-redis redis-cli INFO stats | grep keyspace
```

## Teste de Carga (Opcional)

Instale o Apache Bench (ab):
```bash
sudo apt-get install apache2-utils  # Ubuntu/Debian
```

Teste a performance do endpoint:
```bash
# 1000 requisições, 10 concorrentes
ab -n 1000 -c 10 http://localhost:8000/api/features/CUST00001/
```

## Solução de Problemas

### Verificar logs dos serviços

```bash
# Logs do Django
docker-compose logs -f web

# Logs do Redis
docker-compose logs -f redis

# Logs do MongoDB
docker-compose logs -f mongodb
```

### Reiniciar serviços

```bash
docker-compose restart
```

### Limpar todos os dados

```bash
# Limpar Redis
docker exec cache-demo-redis redis-cli FLUSHALL

# Limpar MongoDB
docker exec -it cache-demo-mongodb mongosh cache_demo --eval "db.customer_features.deleteMany({})"
```

## Resumo do Comportamento Esperado

| Cenário | Status Redis | Status MongoDB | Tempo de Resposta | Mensagem no Log |
|----------|-------------|----------------|---------------|-------------|
| Primeira busca | MISS | HIT | ~20-50ms | Cache MISS Redis, HIT MongoDB |
| Busca em cache | HIT | Não verificado | <1ms | Cache HIT (Redis) |
| Não encontrado | MISS | MISS | ~20-50ms | Features not found |
| Após criar | HIT | HIT | <1ms | Cache HIT (Redis) |

## Critérios de Sucesso

- Verificação de saúde retorna status saudável para ambos os serviços  
- Operação de criação armazena em Redis e MongoDB  
- Primeira leitura acerta o MongoDB e aquece o Redis  
- Leituras subsequentes acertam o Redis (rápido)  
- Delete remove de ambos os armazenamentos  
- Expiração TTL funciona corretamente  
- Operações em lote completam com sucesso  

---

**Nota**: Todos os testes assumem que os serviços estão rodando via `docker-compose up -d`
