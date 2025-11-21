"""
Management command to populate sample data for testing the cache strategy
"""

import random
from django.core.management.base import BaseCommand
from django.conf import settings
from api.services import FeaturesService


class Command(BaseCommand):
    help = "Populate sample customer features for testing the cache strategy"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=10,
            help="Number of sample customers to create (default: 10)",
        )

    def handle(self, *args, **options):
        count = options["count"]

        self.stdout.write(self.style.WARNING(f"Creating {count} sample customers..."))

        # Initialize service
        service = FeaturesService(
            redis_host=settings.REDIS_HOST,
            redis_port=settings.REDIS_PORT,
            redis_db=settings.REDIS_DB,
            redis_ttl=settings.REDIS_TTL,
            mongo_uri=settings.MONGO_URI,
            mongo_db=settings.MONGO_DB,
        )

        # Generate sample data
        features_list = []
        for i in range(count):
            customer_id = f"CUST{str(i + 1).zfill(5)}"
            features = {
                "payment_history_score": round(random.uniform(0.5, 1.0), 2),
                "credit_utilization": round(random.uniform(0.1, 0.8), 2),
                "account_age_months": random.randint(6, 120),
                "recent_inquiries": random.randint(0, 5),
                "debt_to_income": round(random.uniform(0.1, 0.6), 2),
                "on_time_payments_pct": round(random.uniform(0.7, 1.0), 2),
                "total_accounts": random.randint(1, 15),
                "delinquent_accounts": random.randint(0, 3),
                "credit_mix_score": round(random.uniform(0.5, 1.0), 2),
                "length_of_credit_history": random.randint(12, 240),
            }

            features_list.append({"customer_id": customer_id, "features": features})

        # Bulk insert
        stats = service.bulk_set_features(
            features_list=features_list, model_version="v1.0.0", ttl_days=7
        )

        self.stdout.write(
            self.style.SUCCESS(f"✓ Successfully created {stats['success']} customers")
        )

        if stats["failed"] > 0:
            self.stdout.write(
                self.style.ERROR(f"✗ Failed to create {stats['failed']} customers")
            )

        # Display sample
        self.stdout.write("\n" + self.style.WARNING("Sample data:"))
        for item in features_list[:3]:
            self.stdout.write(
                f"  • {item['customer_id']}: {list(item['features'].keys())[:3]}..."
            )

        self.stdout.write("\n" + self.style.SUCCESS("You can now test the API:"))
        self.stdout.write(f"  curl http://localhost:8000/api/features/CUST00001/")
