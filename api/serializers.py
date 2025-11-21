"""
API Serializers for Feature Management
"""

from rest_framework import serializers


class FeatureSerializer(serializers.Serializer):
    """Serializer for feature data"""

    customer_id = serializers.CharField(max_length=100)
    features = serializers.DictField()
    calculated_at = serializers.CharField(read_only=True)
    model_version = serializers.CharField(read_only=True)
    expires_at = serializers.CharField(read_only=True)


class CreateFeatureSerializer(serializers.Serializer):
    """Serializer for creating/updating features"""

    customer_id = serializers.CharField(max_length=100)
    features = serializers.DictField(
        help_text="Dictionary containing feature key-value pairs"
    )
    model_version = serializers.CharField(default="v1.0.0", required=False)
    ttl_days = serializers.IntegerField(
        default=7, min_value=1, max_value=30, required=False
    )


class BulkFeatureSerializer(serializers.Serializer):
    """Serializer for bulk feature operations"""

    features_list = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of feature objects with customer_id and features",
    )
    model_version = serializers.CharField(default="v1.0.0", required=False)
    ttl_days = serializers.IntegerField(
        default=7, min_value=1, max_value=30, required=False
    )


class HealthCheckSerializer(serializers.Serializer):
    """Serializer for health check response"""

    redis = serializers.DictField()
    mongodb = serializers.DictField()
