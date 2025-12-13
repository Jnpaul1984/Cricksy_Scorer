# MCP Tool Contracts – Cricksy Scorer (Minimum Set)

## DB Tools

### 1. feedback.list
- **Purpose:** List user feedback submissions for a time window.
- **Input Schema:**
```json
{
  "since": "2025-12-01T00:00:00Z",
  "until": "2025-12-12T23:59:59Z",
  "limit": 100,
  "offset": 0
}
```
- **Output Schema:**
```json
{
  "items": [
    {
      "id": "string",
      "submitted_at": "2025-12-12T12:34:56Z",
      "user_id": "string",
      "page": "string",
      "type": "bug|suggestion|praise|other",
      "severity": "low|med|high",
      "text": "string"
    }
  ]
}
```
- **Auth/Role:** analyst_pro, product, admin

### 2. feedback.stats
- **Purpose:** Aggregate feedback counts by type, page, and severity.
- **Input Schema:**
```json
{
  "since": "2025-12-01T00:00:00Z",
  "until": "2025-12-12T23:59:59Z"
}
```
- **Output Schema:**
```json
{
  "countsByType": { "bug": 12, "suggestion": 5 },
  "countsByPage": { "/scoring": 8, "/login": 2 },
  "countsBySeverity": { "high": 3, "med": 7, "low": 5 }
}
```
- **Auth/Role:** analyst_pro, product, admin

### 3. usage.summary
- **Purpose:** Summarize usage and token/cost by feature, user, or org.
- **Input Schema:**
```json
{
  "since": "2025-12-01T00:00:00Z",
  "until": "2025-12-12T23:59:59Z",
  "groupBy": "feature|user|org"
}
```
- **Output Schema:**
```json
{
  "totals": { "tokens": 42000, "cost": 1.05 },
  "byFeature": [ { "feature": "Score Predictor", "tokens": 12000, "cost": 0.30 } ],
  "byUser": [ { "user_id": "u123", "tokens": 5000 } ],
  "byOrg": [ { "org_id": "o1", "tokens": 20000 } ]
}
```
- **Auth/Role:** analyst_pro, engineering, admin

### 4. errors.recent
- **Purpose:** List recent backend errors for a time window.
- **Input Schema:**
```json
{
  "since": "2025-12-01T00:00:00Z",
  "until": "2025-12-12T23:59:59Z",
  "limit": 100
}
```
- **Output Schema:**
```json
{
  "items": [
    {
      "id": "string",
      "timestamp": "2025-12-12T12:34:56Z",
      "endpoint": "/games/score",
      "status": 500,
      "stack": "string",
      "user_id": "string|null"
    }
  ]
}
```
- **Auth/Role:** analyst_pro, engineering, admin

### 5. events.pageviews
- **Purpose:** Summarize page view events by route or group.
- **Input Schema:**
```json
{
  "since": "2025-12-01T00:00:00Z",
  "until": "2025-12-12T23:59:59Z",
  "groupBy": "route|user|org"
}
```
- **Output Schema:**
```json
{
  "totals": 1200,
  "byRoute": [ { "route": "/scoring", "views": 400 } ]
}
```
- **Auth/Role:** analyst_pro, product, admin

---

## System Tools

### 6. config.runtime
- **Purpose:** Report current runtime config (safe, no secrets).
- **Input Schema:**
```json
{}
```
- **Output Schema:**
```json
{
  "env": "production|staging|dev",
  "version": "v1.2.3",
  "commit": "abcdef1",
  "apiBaseUrl": "https://api.cricksy.com"
}
```
- **Auth/Role:** analyst_pro, engineering, admin

### 7. health.check
- **Purpose:** Report backend, DB, queue, and deploy health.
- **Input Schema:**
```json
{}
```
- **Output Schema:**
```json
{
  "backendOk": true,
  "dbOk": true,
  "queueOk": true,
  "lastDeploy": "2025-12-12T10:00:00Z"
}
```
- **Auth/Role:** analyst_pro, engineering, admin

---

All contracts above are stable, do not leak secrets, and are suitable for agent/LLM use.