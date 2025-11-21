"""
Features Service
Gerencia features pré-calculadas dos clientes com cache Redis + MongoDB
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# Redis (instalar: pip install redis)
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# MongoDB (instalar: pip install pymongo)
try:
    from pymongo import MongoClient

    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False

logger = logging.getLogger(__name__)


class FeaturesService:
    """
    Service para recuperar features pré-calculadas de clientes

    Usa Redis como cache L1 (rápido) e MongoDB como persistência (L2)

    Estrutura de Features:
    {
        "customer_id": "CUST12345",
        "features": {
            "payment_history_score": 0.85,
            "credit_utilization": 0.30,
            "account_age_months": 36,
            "recent_inquiries": 2,
            "debt_to_income": 0.35,
            "on_time_payments_pct": 0.95,
            "total_accounts": 5,
            "delinquent_accounts": 0,
            ... (mais features)
        },
        "calculated_at": "2025-11-02T10:00:00Z",
        "model_version": "v1.0.0",
        "expires_at": "2025-11-09T10:00:00Z"  # TTL de 7 dias
    }
    """

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_ttl: int = 604800,  # 7 dias em segundos
        mongo_uri: str = "mongodb://localhost:27017/",
        mongo_db: str = "credit_score",
        use_redis: bool = True,
        use_mongo: bool = True,
    ):
        """
        Inicializa o serviço de features

        Args:
            redis_host: Host do Redis
            redis_port: Porta do Redis
            redis_db: Database do Redis
            redis_ttl: Time-to-live do cache em segundos (padrão: 7 dias)
            mongo_uri: URI de conexão do MongoDB
            mongo_db: Nome do database MongoDB
            use_redis: Se deve usar Redis (para testes pode desabilitar)
            use_mongo: Se deve usar MongoDB (para testes pode desabilitar)
        """
        self.redis_ttl = redis_ttl
        self.use_redis = use_redis and REDIS_AVAILABLE
        self.use_mongo = use_mongo and MONGO_AVAILABLE

        # Conecta ao Redis (cache)
        self.redis_client = None
        if self.use_redis:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                # Testa conexão
                self.redis_client.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.warning(f"Redis not available: {e}. Running without cache.")
                self.redis_client = None
                self.use_redis = False

        # Conecta ao MongoDB (persistência)
        self.mongo_client = None
        self.mongo_collection = None
        if self.use_mongo:
            try:
                self.mongo_client = MongoClient(
                    mongo_uri, serverSelectionTimeoutMS=2000
                )
                # Testa conexão
                self.mongo_client.server_info()
                db = self.mongo_client[mongo_db]
                self.mongo_collection = db["customer_features"]

                # Cria índice no customer_id para busca rápida
                self.mongo_collection.create_index("customer_id", unique=True)

                # Cria índice TTL para expiração automática
                self.mongo_collection.create_index("expires_at", expireAfterSeconds=0)

                logger.info("MongoDB connection established")
            except Exception as e:
                logger.warning(
                    f"MongoDB not available: {e}. Running without persistence."
                )
                self.mongo_client = None
                self.mongo_collection = None
                self.use_mongo = False

    def _get_redis_key(self, customer_id: str) -> str:
        """Gera chave Redis para um customer_id"""
        return f"features:{customer_id}"

    def get_features(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera features de um cliente (Redis → MongoDB → None)

        Args:
            customer_id: ID do cliente

        Returns:
            Dict com features ou None se não encontrado
        """
        logger.debug(f"Fetching features for customer_id: {customer_id}")

        # Tenta Redis primeiro (cache L1)
        if self.use_redis and self.redis_client:
            try:
                cached = self.redis_client.get(self._get_redis_key(customer_id))
                if cached:
                    logger.info(f"Features cache HIT for {customer_id} (Redis)")
                    return json.loads(cached)
            except Exception as e:
                logger.error(f"Redis get error: {e}")

        # Tenta MongoDB (persistência L2)
        if self.use_mongo and self.mongo_collection is not None:
            try:
                doc = self.mongo_collection.find_one(
                    {"customer_id": customer_id},
                    {"_id": 0},  # Exclui o _id do MongoDB
                )

                if doc:
                    logger.info(
                        f"Features cache MISS Redis, HIT MongoDB for {customer_id}"
                    )

                    # Atualiza o cache Redis
                    if self.use_redis and self.redis_client:
                        try:
                            self.redis_client.setex(
                                self._get_redis_key(customer_id),
                                self.redis_ttl,
                                json.dumps(doc, default=str),
                            )
                        except Exception as e:
                            logger.error(f"Redis set error: {e}")

                    return doc
            except Exception as e:
                logger.error(f"MongoDB get error: {e}")

        logger.warning(f"Features not found for customer_id: {customer_id}")
        return None

    def set_features(
        self,
        customer_id: str,
        features: Dict[str, Any],
        model_version: str = "v1.0.0",
        ttl_days: int = 7,
    ) -> bool:
        """
        Armazena features de um cliente (MongoDB + Redis)

        Args:
            customer_id: ID do cliente
            features: Dicionário com as features
            model_version: Versão do modelo que gerou as features
            ttl_days: Dias até expiração (padrão: 7)

        Returns:
            bool: True se sucesso, False se falhou
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(days=ttl_days)

        doc = {
            "customer_id": customer_id,
            "features": features,
            "calculated_at": now.isoformat() + "Z",
            "model_version": model_version,
            "expires_at": expires_at,
        }

        success = False

        # Salva no MongoDB (persistência)
        if self.use_mongo and self.mongo_collection is not None:
            try:
                self.mongo_collection.replace_one(
                    {"customer_id": customer_id}, doc, upsert=True
                )
                logger.info(f"Features saved to MongoDB for {customer_id}")
                success = True
            except Exception as e:
                logger.error(f"MongoDB set error: {e}")

        # Salva no Redis (cache)
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.setex(
                    self._get_redis_key(customer_id),
                    self.redis_ttl,
                    json.dumps(doc, default=str),
                )
                logger.info(f"Features cached in Redis for {customer_id}")
                success = True
            except Exception as e:
                logger.error(f"Redis set error: {e}")

        return success

    def delete_features(self, customer_id: str) -> bool:
        """
        Remove features de um cliente (MongoDB + Redis)

        Args:
            customer_id: ID do cliente

        Returns:
            bool: True se removido, False se não encontrado
        """
        deleted = False

        # Remove do Redis
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.delete(self._get_redis_key(customer_id))
                logger.info(f"Features removed from Redis for {customer_id}")
                deleted = True
            except Exception as e:
                logger.error(f"Redis delete error: {e}")

        # Remove do MongoDB
        if self.use_mongo and self.mongo_collection is not None:
            try:
                result = self.mongo_collection.delete_one({"customer_id": customer_id})
                if result.deleted_count > 0:
                    logger.info(f"Features removed from MongoDB for {customer_id}")
                    deleted = True
            except Exception as e:
                logger.error(f"MongoDB delete error: {e}")

        return deleted

    def bulk_set_features(
        self, features_list: list, model_version: str = "v1.0.0", ttl_days: int = 7
    ) -> Dict[str, int]:
        """
        Armazena features de múltiplos clientes em batch

        Args:
            features_list: Lista de dicts com customer_id e features
                Formato: [{"customer_id": "...", "features": {...}}, ...]
            model_version: Versão do modelo
            ttl_days: Dias até expiração

        Returns:
            Dict com contadores: {"success": int, "failed": int}
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(days=ttl_days)

        stats = {"success": 0, "failed": 0}

        # Prepara documentos
        docs = []
        for item in features_list:
            doc = {
                "customer_id": item["customer_id"],
                "features": item["features"],
                "calculated_at": now.isoformat() + "Z",
                "model_version": model_version,
                "expires_at": expires_at,
            }
            docs.append(doc)

        # Bulk insert no MongoDB
        if self.use_mongo and self.mongo_collection is not None:
            try:
                from pymongo import ReplaceOne

                operations = [
                    ReplaceOne({"customer_id": doc["customer_id"]}, doc, upsert=True)
                    for doc in docs
                ]

                result = self.mongo_collection.bulk_write(operations, ordered=False)
                stats["success"] = result.upserted_count + result.modified_count

                logger.info(f"Bulk insert to MongoDB: {stats['success']} documents")
            except Exception as e:
                logger.error(f"MongoDB bulk insert error: {e}")
                stats["failed"] = len(docs)

        # Cacheia no Redis (em pipeline para performance)
        if self.use_redis and self.redis_client:
            try:
                pipe = self.redis_client.pipeline()
                for doc in docs:
                    pipe.setex(
                        self._get_redis_key(doc["customer_id"]),
                        self.redis_ttl,
                        json.dumps(doc, default=str),
                    )
                pipe.execute()

                logger.info(f"Bulk cache to Redis: {len(docs)} keys")
            except Exception as e:
                logger.error(f"Redis bulk set error: {e}")

        return stats

    def health_check(self) -> Dict[str, Any]:
        """
        Verifica saúde das conexões

        Returns:
            Dict com status de Redis e MongoDB
        """
        health = {
            "redis": {"available": False, "status": "unavailable"},
            "mongodb": {"available": False, "status": "unavailable"},
        }

        # Check Redis
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.ping()
                info = self.redis_client.info("stats")
                health["redis"] = {
                    "available": True,
                    "status": "healthy",
                    "total_keys": self.redis_client.dbsize(),
                    "used_memory": info.get("used_memory_human", "N/A"),
                }
            except Exception as e:
                health["redis"] = {
                    "available": False,
                    "status": "unhealthy",
                    "error": str(e),
                }

        # Check MongoDB
        if self.use_mongo and self.mongo_client:
            try:
                self.mongo_client.server_info()
                count = self.mongo_collection.count_documents({})
                health["mongodb"] = {
                    "available": True,
                    "status": "healthy",
                    "documents_count": count,
                    "collection": "customer_features",
                }
            except Exception as e:
                health["mongodb"] = {
                    "available": False,
                    "status": "unhealthy",
                    "error": str(e),
                }

        return health
