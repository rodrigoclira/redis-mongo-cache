"""
API Views for L1 Cache Strategy Demo
Demonstrates Redis (L1 Cache) + MongoDB (L2 Persistence)
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.conf import settings

from .services import FeaturesService
from .serializers import (
    FeatureSerializer,
    CreateFeatureSerializer,
    BulkFeatureSerializer,
    HealthCheckSerializer,
)

logger = logging.getLogger(__name__)


class FeaturesServiceMixin:
    """Mixin to provide features service instance"""

    def get_features_service(self):
        """Get or create FeaturesService instance"""
        if not hasattr(self, "_features_service"):
            self._features_service = FeaturesService(
                redis_host=settings.REDIS_HOST,
                redis_port=settings.REDIS_PORT,
                redis_db=settings.REDIS_DB,
                redis_ttl=settings.REDIS_TTL,
                mongo_uri=settings.MONGO_URI,
                mongo_db=settings.MONGO_DB,
            )
        return self._features_service


class FeatureRetrieveView(FeaturesServiceMixin, APIView):
    """
    Retrieve feature data for a specific customer

    This endpoint demonstrates the L1 cache strategy:
    1. First tries to get data from Redis (L1 - fast cache)
    2. If not found in Redis, queries MongoDB (L2 - persistent storage)
    3. If found in MongoDB, automatically updates Redis cache
    """

    @swagger_auto_schema(
        operation_description="Get features for a customer (Redis → MongoDB)",
        responses={
            200: FeatureSerializer(),
            404: "Features not found",
            500: "Internal server error",
        },
    )
    def get(self, request, customer_id):
        """Get features for a customer"""
        try:
            service = self.get_features_service()
            features = service.get_features(customer_id)

            if features:
                serializer = FeatureSerializer(features)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": f"Features not found for customer_id: {customer_id}"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        except Exception as e:
            logger.error(f"Error retrieving features: {str(e)}", exc_info=True)
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class FeatureCreateUpdateView(FeaturesServiceMixin, APIView):
    """
    Create or update feature data for a customer

    This endpoint stores data in both:
    1. MongoDB (persistent storage)
    2. Redis (fast cache with TTL)
    """

    @swagger_auto_schema(
        operation_description="Create or update features for a customer",
        request_body=CreateFeatureSerializer,
        responses={
            201: FeatureSerializer(),
            400: "Bad request",
            500: "Internal server error",
        },
    )
    def post(self, request):
        """Create or update features"""
        serializer = CreateFeatureSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = serializer.validated_data
            service = self.get_features_service()

            success = service.set_features(
                customer_id=data["customer_id"],
                features=data["features"],
                model_version=data.get("model_version", "v1.0.0"),
                ttl_days=data.get("ttl_days", 7),
            )

            if success:
                # Retrieve the stored data to return
                stored_features = service.get_features(data["customer_id"])
                result_serializer = FeatureSerializer(stored_features)
                return Response(result_serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {"error": "Failed to store features"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        except Exception as e:
            logger.error(f"Error creating features: {str(e)}", exc_info=True)
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class FeatureDeleteView(FeaturesServiceMixin, APIView):
    """
    Delete feature data for a customer

    Removes data from both Redis and MongoDB
    """

    @swagger_auto_schema(
        operation_description="Delete features for a customer",
        responses={
            204: "Features deleted successfully",
            404: "Features not found",
            500: "Internal server error",
        },
    )
    def delete(self, request, customer_id):
        """Delete features for a customer"""
        try:
            service = self.get_features_service()
            deleted = service.delete_features(customer_id)

            if deleted:
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(
                    {"error": f"Features not found for customer_id: {customer_id}"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        except Exception as e:
            logger.error(f"Error deleting features: {str(e)}", exc_info=True)
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BulkFeatureCreateView(FeaturesServiceMixin, APIView):
    """
    Bulk create/update feature data for multiple customers

    Efficiently stores data for multiple customers using batch operations
    """

    @swagger_auto_schema(
        operation_description="Bulk create/update features for multiple customers",
        request_body=BulkFeatureSerializer,
        responses={
            201: openapi.Response(
                description="Bulk operation completed",
                examples={
                    "application/json": {
                        "success": 10,
                        "failed": 0,
                        "message": "Bulk operation completed",
                    }
                },
            ),
            400: "Bad request",
            500: "Internal server error",
        },
    )
    def post(self, request):
        """Bulk create/update features"""
        serializer = BulkFeatureSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = serializer.validated_data
            service = self.get_features_service()

            stats = service.bulk_set_features(
                features_list=data["features_list"],
                model_version=data.get("model_version", "v1.0.0"),
                ttl_days=data.get("ttl_days", 7),
            )

            return Response(
                {
                    "success": stats["success"],
                    "failed": stats["failed"],
                    "message": "Bulk operation completed",
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Error in bulk operation: {str(e)}", exc_info=True)
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class HealthCheckView(FeaturesServiceMixin, APIView):
    """
    Health check endpoint

    Returns the status of Redis and MongoDB connections
    """

    @swagger_auto_schema(
        operation_description="Check health status of Redis and MongoDB",
        responses={200: HealthCheckSerializer(), 500: "Internal server error"},
    )
    def get(self, request):
        """Health check"""
        try:
            service = self.get_features_service()
            health = service.health_check()

            # Determine overall status
            overall_status = status.HTTP_200_OK
            if not health["redis"]["available"] or not health["mongodb"]["available"]:
                overall_status = status.HTTP_503_SERVICE_UNAVAILABLE

            serializer = HealthCheckSerializer(health)
            return Response(serializer.data, status=overall_status)
        except Exception as e:
            logger.error(f"Error in health check: {str(e)}", exc_info=True)
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CacheStrategyInfoView(APIView):
    """
    Information about the L1 cache strategy implementation

    Provides documentation about how the caching strategy works
    """

    @swagger_auto_schema(
        operation_description="Get information about the L1 cache strategy",
        responses={
            200: openapi.Response(
                description="Cache strategy information",
                examples={
                    "application/json": {
                        "strategy": "L1 Cache with Redis and MongoDB",
                        "description": "Two-tier caching strategy...",
                    }
                },
            )
        },
    )
    def get(self, request):
        """Get cache strategy information"""
        info = {
            "strategy": "L1 Cache with Redis and MongoDB",
            "description": (
                "This project demonstrates a two-tier caching strategy where "
                "Redis acts as the L1 (Level 1) cache for fast data access, "
                "and MongoDB serves as the L2 persistent storage layer."
            ),
            "flow": {
                "read": [
                    "1. Client requests data for a customer_id",
                    "2. System checks Redis (L1 cache) first",
                    "3. If found in Redis → Return immediately (cache HIT)",
                    "4. If not in Redis → Query MongoDB (L2 storage)",
                    "5. If found in MongoDB → Update Redis cache and return data",
                    "6. If not found anywhere → Return 404",
                ],
                "write": [
                    "1. Client sends data to create/update",
                    "2. System writes to MongoDB (persistent storage)",
                    "3. System also caches in Redis with TTL",
                    "4. Both operations ensure data consistency",
                ],
            },
            "benefits": {
                "redis": [
                    "In-memory storage for extremely fast reads (microseconds)",
                    "Automatic expiration with TTL (Time To Live)",
                    "Reduces load on MongoDB",
                    "Handles high-frequency read operations efficiently",
                ],
                "mongodb": [
                    "Persistent storage - data survives restarts",
                    "Handles complex queries and indexing",
                    "Serves as source of truth for data",
                    "Automatic TTL-based document expiration",
                ],
            },
            "performance": {
                "redis_read": "< 1ms (in-memory)",
                "mongodb_read": "10-50ms (disk-based, indexed)",
                "cache_hit_ratio": "Typically 80-95% with proper TTL configuration",
            },
            "endpoints": {
                "GET /api/features/{customer_id}/": "Retrieve features (demonstrates cache strategy)",
                "POST /api/features/": "Create/update features",
                "DELETE /api/features/{customer_id}/": "Delete features",
                "POST /api/features/bulk/": "Bulk create/update features",
                "GET /api/health/": "Check Redis and MongoDB status",
                "GET /api/info/": "This endpoint - strategy information",
            },
        }
        return Response(info, status=status.HTTP_200_OK)
