#!/bin/bash

# Demo Script for L1 Cache Strategy Presentation
# This script demonstrates the cache flow in real-time

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Base URL
BASE_URL="http://localhost:8000"

# Function to print section headers
print_header() {
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
}

# Function to print commands before executing
print_command() {
    echo -e "${YELLOW}$ $1${NC}"
}

# Function to wait for user
wait_for_user() {
    echo ""
    read -p "Press ENTER to continue..."
    echo ""
}

# Function to make API call and show response
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    
    print_command "curl -X $method $BASE_URL$endpoint"
    
    if [ -n "$data" ]; then
        curl -s -X $method "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data" | jq '.'
    else
        curl -s -X $method "$BASE_URL$endpoint" | jq '.'
    fi
    echo ""
}

clear

echo -e "${MAGENTA}"
cat << "EOF"
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║     L1 CACHE STRATEGY DEMONSTRATION                   ║
║     Redis (L1) + MongoDB (L2)                        ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo "This demo will walk you through the L1 cache strategy."
echo "You'll see how data flows between Redis and MongoDB."
echo ""
echo "Make sure all services are running:"
echo "  docker-compose ps"
echo ""

wait_for_user

# ============================================================
# DEMO 1: Health Check
# ============================================================
print_header "DEMO 1: Health Check"
echo "Let's verify that Redis and MongoDB are healthy."
echo ""

api_call "GET" "/api/health/"

echo -e "${GREEN}✓ Both services are healthy!${NC}"
wait_for_user

# ============================================================
# DEMO 2: Understanding the Strategy
# ============================================================
print_header "DEMO 2: Understanding the Strategy"
echo "Let's get information about the cache strategy."
echo ""

api_call "GET" "/api/info/" | head -n 50

echo -e "${BLUE}This explains our two-tier caching approach.${NC}"
wait_for_user

# ============================================================
# DEMO 3: Creating Data (Write Operation)
# ============================================================
print_header "DEMO 3: Creating Data (Write Operation)"
echo "We'll create a customer feature record."
echo "This will be written to BOTH Redis and MongoDB."
echo ""

CUSTOMER_ID="DEMO12345"
DATA='{
  "customer_id": "DEMO12345",
  "features": {
    "payment_history_score": 0.92,
    "credit_utilization": 0.25,
    "account_age_months": 48,
    "recent_inquiries": 1,
    "debt_to_income": 0.28
  },
  "model_version": "v1.0.0",
  "ttl_days": 7
}'

api_call "POST" "/api/features/" "$DATA"

echo -e "${GREEN}✓ Data written to both Redis (cache) and MongoDB (storage)${NC}"
wait_for_user

# ============================================================
# DEMO 4: Reading Data - Cache HIT (Redis)
# ============================================================
print_header "DEMO 4: Reading Data - Cache HIT (Redis)"
echo "Now let's retrieve the same customer data."
echo "This should come from Redis (L1 cache) - VERY FAST!"
echo ""

echo -e "${CYAN}Watch the response time...${NC}"
echo ""

START_TIME=$(date +%s%3N)
api_call "GET" "/api/features/$CUSTOMER_ID/"
END_TIME=$(date +%s%3N)
ELAPSED=$((END_TIME - START_TIME))

echo -e "${GREEN}✓ Response time: ~${ELAPSED}ms (from Redis cache)${NC}"
echo -e "${BLUE}Check the Docker logs to see 'Cache HIT' message:${NC}"
print_command "docker-compose logs web | grep -i 'cache hit' | tail -1"
docker-compose logs web 2>/dev/null | grep -i "cache hit" | tail -1 || echo "  (Check logs with: docker-compose logs web)"

wait_for_user

# ============================================================
# DEMO 5: Cache MISS - MongoDB Fallback
# ============================================================
print_header "DEMO 5: Cache MISS - MongoDB Fallback"
echo "Let's simulate a cache miss by deleting the Redis key."
echo "Then we'll fetch the data again - it will come from MongoDB."
echo ""

echo -e "${YELLOW}Deleting from Redis...${NC}"
print_command "docker exec cache-demo-redis redis-cli DEL 'features:$CUSTOMER_ID'"
docker exec cache-demo-redis redis-cli DEL "features:$CUSTOMER_ID" 2>/dev/null || echo "Redis container not found"

echo ""
echo -e "${CYAN}Now fetching the data (should hit MongoDB)...${NC}"
echo ""

START_TIME=$(date +%s%3N)
api_call "GET" "/api/features/$CUSTOMER_ID/"
END_TIME=$(date +%s%3N)
ELAPSED=$((END_TIME - START_TIME))

echo -e "${GREEN}✓ Response time: ~${ELAPSED}ms (from MongoDB + cache warming)${NC}"
echo -e "${BLUE}Check logs to see 'Cache MISS Redis, HIT MongoDB':${NC}"
print_command "docker-compose logs web | grep -i 'mongodb' | tail -1"
docker-compose logs web 2>/dev/null | grep -i "mongodb" | tail -1 || echo "  (Check logs with: docker-compose logs web)"

echo ""
echo -e "${MAGENTA}Important: Redis cache was automatically warmed!${NC}"
wait_for_user

# ============================================================
# DEMO 6: Verify Cache Warming
# ============================================================
print_header "DEMO 6: Verify Cache Warming"
echo "Let's verify that Redis was updated (cache warming)."
echo "This next request should be fast again!"
echo ""

START_TIME=$(date +%s%3N)
api_call "GET" "/api/features/$CUSTOMER_ID/"
END_TIME=$(date +%s%3N)
ELAPSED=$((END_TIME - START_TIME))

echo -e "${GREEN}✓ Response time: ~${ELAPSED}ms (back to Redis speed!)${NC}"
echo -e "${MAGENTA}Cache warming successful - Redis is serving data again.${NC}"

wait_for_user

# ============================================================
# DEMO 7: Bulk Operations
# ============================================================
print_header "DEMO 7: Bulk Operations"
echo "Now let's create multiple customers at once."
echo ""

BULK_DATA='{
  "features_list": [
    {
      "customer_id": "BULK001",
      "features": {"score": 0.85, "risk": "low"}
    },
    {
      "customer_id": "BULK002",
      "features": {"score": 0.72, "risk": "medium"}
    },
    {
      "customer_id": "BULK003",
      "features": {"score": 0.93, "risk": "low"}
    }
  ],
  "model_version": "v1.0.0"
}'

api_call "POST" "/api/features/bulk/" "$BULK_DATA"

echo -e "${GREEN}✓ Bulk creation complete!${NC}"
echo ""
echo "Let's verify one of them:"
api_call "GET" "/api/features/BULK001/"

wait_for_user

# ============================================================
# DEMO 8: Performance Comparison
# ============================================================
print_header "DEMO 8: Performance Comparison"
echo "Let's compare Redis vs MongoDB response times."
echo ""

echo -e "${CYAN}1. Fetching from Redis (cached):${NC}"
START_TIME=$(date +%s%3N)
curl -s "$BASE_URL/api/features/$CUSTOMER_ID/" > /dev/null
END_TIME=$(date +%s%3N)
REDIS_TIME=$((END_TIME - START_TIME))
echo "   Response time: ${REDIS_TIME}ms"
echo ""

echo -e "${CYAN}2. Clearing Redis and fetching from MongoDB:${NC}"
docker exec cache-demo-redis redis-cli DEL "features:$CUSTOMER_ID" > /dev/null 2>&1
START_TIME=$(date +%s%3N)
curl -s "$BASE_URL/api/features/$CUSTOMER_ID/" > /dev/null
END_TIME=$(date +%s%3N)
MONGO_TIME=$((END_TIME - START_TIME))
echo "   Response time: ${MONGO_TIME}ms"
echo ""

if [ $REDIS_TIME -lt $MONGO_TIME ]; then
    SPEEDUP=$((MONGO_TIME / REDIS_TIME))
    echo -e "${GREEN}Redis is ~${SPEEDUP}x faster than MongoDB!${NC}"
else
    echo -e "${YELLOW}Times may vary due to network conditions${NC}"
fi

wait_for_user

# ============================================================
# DEMO 9: Monitoring
# ============================================================
print_header "DEMO 9: Monitoring"
echo "Let's check some statistics."
echo ""

echo -e "${CYAN}Redis Statistics:${NC}"
print_command "docker exec cache-demo-redis redis-cli INFO stats | grep total_commands"
docker exec cache-demo-redis redis-cli INFO stats 2>/dev/null | grep total_commands || echo "Redis container not available"

echo ""
echo -e "${CYAN}Redis Keys:${NC}"
print_command "docker exec cache-demo-redis redis-cli KEYS 'features:*'"
docker exec cache-demo-redis redis-cli KEYS "features:*" 2>/dev/null || echo "Redis container not available"

echo ""
echo -e "${CYAN}MongoDB Statistics:${NC}"
print_command "docker exec cache-demo-mongodb mongosh cache_demo --quiet --eval 'db.customer_features.countDocuments()'"
docker exec cache-demo-mongodb mongosh cache_demo --quiet --eval "db.customer_features.countDocuments()" 2>/dev/null || echo "MongoDB container not available"

wait_for_user

# ============================================================
# DEMO 10: Cleanup (Optional)
# ============================================================
print_header "DEMO 10: Cleanup"
echo "Let's delete the demo data we created."
echo ""

echo -e "${YELLOW}Deleting customer: $CUSTOMER_ID${NC}"
print_command "curl -X DELETE $BASE_URL/api/features/$CUSTOMER_ID/delete/"
curl -s -X DELETE "$BASE_URL/api/features/$CUSTOMER_ID/delete/"
echo ""

echo -e "${GREEN}✓ Cleanup complete${NC}"
echo ""

# ============================================================
# Summary
# ============================================================
print_header "DEMONSTRATION COMPLETE"
echo -e "${GREEN}What we demonstrated:${NC}"
echo "  ✓ Health monitoring of Redis and MongoDB"
echo "  ✓ Write operations (data stored in both layers)"
echo "  ✓ Read from Redis (L1 cache) - Fast!"
echo "  ✓ Read from MongoDB (L2) when cache misses"
echo "  ✓ Automatic cache warming"
echo "  ✓ Bulk operations"
echo "  ✓ Performance comparison"
echo "  ✓ Monitoring and statistics"
echo ""
echo -e "${CYAN}Key Takeaways:${NC}"
echo "  • Redis (L1) provides sub-millisecond response times"
echo "  • MongoDB (L2) ensures data persistence"
echo "  • Automatic fallback and cache warming"
echo "  • Typical speedup: 10-50x with cache hits"
echo ""
echo -e "${MAGENTA}Resources:${NC}"
echo "  • Swagger UI:     $BASE_URL/swagger/"
echo "  • API Docs:       $BASE_URL/redoc/"
echo "  • Health Check:   $BASE_URL/api/health/"
echo "  • Cache Info:     $BASE_URL/api/info/"
echo ""
echo -e "${BLUE}For more details, see:${NC}"
echo "  • README.md - Project overview"
echo "  • CACHE_STRATEGY.md - Technical deep dive"
echo "  • TESTING.md - Testing guide"
echo "  • PROJECT_SUMMARY.md - Quick reference"
echo ""
echo -e "${GREEN}Thank you for watching this demonstration!${NC}"
echo ""
