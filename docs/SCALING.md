# Scaling and Performance Guide

## Overview

This guide covers scaling strategies for the Cricksy Scorer application, focusing on real-time WebSocket performance and horizontal scaling for high-traffic scenarios.

## WebSocket Optimization

### Delta Updates

The application uses delta updates to minimize WebSocket payload sizes:

**Before (Full Snapshot)**:
```json
{
  "id": "game-123",
  "snapshot": {
    "total_runs": 145,
    "total_wickets": 5,
    "overs": "18.3",
    "deliveries": [...120 deliveries...],
    "batting_scorecard": {...full scorecard...},
    "bowling_scorecard": {...full scorecard...}
  }
}
```
Size: ~15-25 KB per update

**After (Delta Update)**:
```json
{
  "id": "game-123",
  "delta": {
    "type": "delta",
    "total_runs": 149,
    "deliveries_delta": {
      "type": "append",
      "new_deliveries": [{"over": 19, "ball": 1, "runs": 4, ...}],
      "from_index": 120
    }
  }
}
```
Size: ~1-2 KB per update

**Benefits**:
- 85-90% reduction in payload size
- Lower latency (less data to transmit)
- Reduced bandwidth costs
- Better mobile performance
- Faster client processing

### Metrics and Monitoring

Access WebSocket metrics:
```bash
curl http://localhost:8000/api/health/ws-metrics
```

Response:
```json
{
  "status": "ok",
  "metrics": {
    "total_emissions": 1247,
    "full_emissions": 15,
    "delta_emissions": 1232,
    "delta_ratio": 0.988,
    "avg_payload_size": 1847.5,
    "min_payload_size": 234,
    "max_payload_size": 18934,
    "avg_latency_ms": 2.3,
    "event_counts": {
      "state:update": 1200,
      "prediction:update": 47
    }
  }
}
```

**Key Metrics to Monitor**:
1. **Delta Ratio**: Should be > 0.85 for optimal performance
2. **Avg Payload Size**: Target < 3 KB for delta updates
3. **Avg Latency**: Should be < 10ms for emissions
4. **Event Counts**: Track event distribution

## Horizontal Scaling

### Single Server Architecture

```
┌─────────┐
│ Clients │
└────┬────┘
     │
┌────▼─────┐
│ FastAPI  │
│ + Socket │
└────┬─────┘
     │
┌────▼────┐
│   DB    │
└─────────┘
```

**Capacity**: ~1,000 concurrent connections per server

### Multi-Server with Redis Adapter

```
┌─────────┐  ┌─────────┐  ┌─────────┐
│Clients  │  │Clients  │  │Clients  │
└────┬────┘  └────┬────┘  └────┬────┘
     │            │            │
┌────▼────┐  ┌───▼─────┐ ┌───▼─────┐
│Server 1 │  │Server 2 │ │Server 3 │
└────┬────┘  └────┬────┘ └────┬────┘
     │            │            │
     └────────────┼────────────┘
                  │
            ┌─────▼─────┐
            │   Redis   │
            │  PubSub   │
            └─────┬─────┘
                  │
            ┌─────▼─────┐
            │    DB     │
            └───────────┘
```

**Capacity**: ~10,000+ concurrent connections

### Enabling Redis Adapter

1. **Configure Redis**:
```bash
export CRICKSY_REDIS_URL=redis://redis-host:6379/0
export CRICKSY_ENABLE_REDIS_ADAPTER=1
```

2. **Install Dependencies**:
```bash
pip install python-socketio[redis]
```

3. **Deploy Multiple Servers**:
```bash
# Server 1
uvicorn backend.main:app --host 0.0.0.0 --port 8001

# Server 2
uvicorn backend.main:app --host 0.0.0.0 --port 8002

# Server 3
uvicorn backend.main:app --host 0.0.0.0 --port 8003
```

4. **Load Balancer** (Nginx example):
```nginx
upstream cricksy_backend {
    ip_hash;  # Sticky sessions for WebSocket
    server localhost:8001;
    server localhost:8002;
    server localhost:8003;
}

server {
    listen 80;
    
    location / {
        proxy_pass http://cricksy_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Database Scaling

### Read Replicas

For read-heavy workloads, use read replicas:

```python
# In config.py
DATABASE_URL = "postgresql+asyncpg://user:pass@primary:5432/db"
DATABASE_READ_REPLICA_URL = "postgresql+asyncpg://user:pass@replica:5432/db"
```

Route read operations to replicas:
```python
# For read-only queries
async with get_read_db() as db:
    games = await db.execute(select(Game).where(...))
```

### Connection Pooling

Optimize connection pool settings:
```python
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,          # Max connections per worker
    max_overflow=10,       # Extra connections under load
    pool_pre_ping=True,    # Verify connections before use
    pool_recycle=3600,     # Recycle connections after 1 hour
)
```

### Caching Strategy

Implement Redis caching for frequently accessed data:

```python
import redis.asyncio as redis

cache = redis.from_url(settings.REDIS_URL)

async def get_game_snapshot(game_id: str):
    # Check cache first
    cached = await cache.get(f"snapshot:{game_id}")
    if cached:
        return json.loads(cached)
    
    # Query database
    snapshot = await fetch_from_db(game_id)
    
    # Cache with 60s TTL
    await cache.setex(
        f"snapshot:{game_id}",
        60,
        json.dumps(snapshot)
    )
    
    return snapshot
```

## Performance Benchmarks

### WebSocket Throughput

| Scenario | Full Snapshots | Delta Updates | Improvement |
|----------|---------------|---------------|-------------|
| Payload Size (avg) | 18 KB | 2 KB | 89% reduction |
| Latency (p95) | 45ms | 8ms | 82% reduction |
| Bandwidth (1000 users) | 18 MB/s | 2 MB/s | 89% reduction |
| Updates/sec (single server) | ~200 | ~1000 | 5x increase |

### API Response Times

| Endpoint | p50 | p95 | p99 |
|----------|-----|-----|-----|
| GET /games/{id} | 15ms | 35ms | 60ms |
| POST /games | 45ms | 120ms | 200ms |
| POST /games/{id}/deliveries | 25ms | 65ms | 120ms |
| GET /api/health/ws-metrics | 2ms | 5ms | 10ms |

## Capacity Planning

### Server Sizing

**Small Deployment** (< 100 concurrent matches):
- 2 API servers (2 vCPU, 4GB RAM each)
- 1 Redis instance (1 vCPU, 2GB RAM)
- 1 PostgreSQL instance (2 vCPU, 8GB RAM)
- 1 Celery worker (2 vCPU, 4GB RAM)

**Medium Deployment** (100-500 concurrent matches):
- 4 API servers (4 vCPU, 8GB RAM each)
- 1 Redis cluster (3 nodes, 2 vCPU, 4GB RAM each)
- 2 PostgreSQL instances (primary + replica, 4 vCPU, 16GB RAM)
- 3 Celery workers (4 vCPU, 8GB RAM each)

**Large Deployment** (500+ concurrent matches):
- 8+ API servers (8 vCPU, 16GB RAM each)
- Redis cluster (6 nodes, 4 vCPU, 8GB RAM each)
- PostgreSQL cluster (primary + 2 replicas, 8 vCPU, 32GB RAM)
- 5+ Celery workers (8 vCPU, 16GB RAM each)
- CDN for static assets

### Cost Optimization

1. **Use Delta Updates**: Reduces bandwidth costs by 85-90%
2. **Cache Aggressively**: Reduces database load and response time
3. **Auto-scaling**: Scale workers based on queue depth
4. **Reserved Instances**: Save 40-60% on cloud costs
5. **Compress WebSocket Messages**: Enable per-message deflate

## Monitoring and Alerting

### Key Metrics

1. **WebSocket**:
   - Active connections
   - Messages/sec
   - Average payload size
   - Delta ratio
   - Emission latency

2. **API**:
   - Requests/sec
   - Response time (p50, p95, p99)
   - Error rate
   - CPU and memory usage

3. **Database**:
   - Connection pool usage
   - Query latency
   - Slow queries
   - Replication lag

4. **Celery**:
   - Queue length
   - Task success rate
   - Processing time
   - Worker health

### Alert Thresholds

```yaml
alerts:
  - name: High WebSocket Latency
    condition: avg_latency_ms > 50
    severity: warning
  
  - name: Low Delta Ratio
    condition: delta_ratio < 0.7
    severity: info
  
  - name: High Error Rate
    condition: error_rate > 0.05
    severity: critical
  
  - name: Database Connection Pool Exhausted
    condition: pool_usage > 0.9
    severity: critical
  
  - name: Celery Queue Backlog
    condition: queue_length > 100
    severity: warning
```

### Prometheus Integration

Example metrics endpoint:
```python
from prometheus_client import Counter, Histogram, Gauge

ws_emissions = Counter('ws_emissions_total', 'Total WebSocket emissions')
ws_latency = Histogram('ws_latency_seconds', 'WebSocket emission latency')
ws_payload_size = Histogram('ws_payload_bytes', 'WebSocket payload size')
active_connections = Gauge('ws_active_connections', 'Active WebSocket connections')
```

## Troubleshooting

### High WebSocket Latency

**Symptoms**: Clients receive updates slowly, high p95 latency

**Solutions**:
1. Enable delta updates (should reduce latency by 80%)
2. Check network bandwidth
3. Scale horizontally with Redis adapter
4. Optimize database queries
5. Use CDN for static assets

### Memory Leaks

**Symptoms**: Memory usage grows over time

**Solutions**:
1. Clear snapshot cache periodically
2. Limit Redis key expiration
3. Monitor with memory profiler
4. Restart workers periodically
5. Check for circular references

### Database Connection Exhaustion

**Symptoms**: "Too many connections" errors

**Solutions**:
1. Increase connection pool size
2. Use connection pooling middleware (PgBouncer)
3. Implement read replicas
4. Add caching layer
5. Optimize query patterns

## Best Practices

1. **Always use delta updates in production**
2. **Monitor WebSocket metrics continuously**
3. **Enable Redis adapter for multi-server deployments**
4. **Cache frequently accessed data**
5. **Use read replicas for read-heavy workloads**
6. **Implement circuit breakers for external dependencies**
7. **Set up comprehensive monitoring and alerting**
8. **Load test before major events**
9. **Have a scaling playbook ready**
10. **Document capacity limits and thresholds**

## Load Testing

Example load test with Locust:

```python
from locust import HttpUser, task, between

class CricksyUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def get_game(self):
        self.client.get("/games/test-game-123")
    
    @task(2)
    def score_delivery(self):
        self.client.post(
            "/games/test-game-123/deliveries",
            json={"runs": 4, "bowler_id": "b1", ...}
        )
    
    @task(1)
    def get_metrics(self):
        self.client.get("/api/health/ws-metrics")
```

Run test:
```bash
locust -f load_test.py --users 1000 --spawn-rate 10
```

## Further Reading

- [Socket.IO Scaling](https://socket.io/docs/v4/using-multiple-nodes/)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [Redis Best Practices](https://redis.io/docs/management/optimization/)
- [FastAPI Performance Tips](https://fastapi.tiangolo.com/deployment/)
