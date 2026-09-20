# Supabase Free-Tier Keep-Alive: Preventing Auto-Pause

## What This Mitigates

Supabase free-tier projects are automatically paused after **7 consecutive
days of database inactivity**. When paused, the entire application becomes
unusable until someone manually restores the project via the Supabase
Dashboard. This document describes how to prevent that with a zero-cost
automated keep-alive ping.

## How Supabase Measures "Activity"

Supabase monitors for **actual SQL database queries** — not HTTP traffic,
API Gateway hits, or dashboard logins. Only requests that execute a real
database operation (SELECT, INSERT, UPDATE, DELETE) count toward resetting
the inactivity timer.

**This means**: a simple HTTP ping to a static endpoint does NOT prevent
auto-pause. The ping target must execute a real database query.

## The Keep-Alive Endpoint

The application's existing health endpoint already satisfies this requirement:

```
GET /api/v1/health
```

- **No authentication required** — safe for anonymous external pings
- **Executes `SELECT 1`** against PostgreSQL on every call
- **Fast and side-effect-free** — adds no meaningful load
- **Returns dependency status** — useful for monitoring
- **Response**: JSON with `status`, `version`, `environment`, `uptime_seconds`,
  and per-dependency health (PostgreSQL, Redis)

Example response:
```json
{
  "status": "degraded",
  "version": "1.0.0",
  "environment": "development",
  "uptime_seconds": 5860.55,
  "dependencies": [
    {"name": "postgresql", "status": "up", "latency_ms": 124.92, "error": null},
    {"name": "redis", "status": "down", "latency_ms": 3027.77, "error": "Timeout connecting to server"}
  ]
}
```

## Ping Interval

- **Supabase inactivity threshold**: 7 days
- **Recommended ping interval**: Every 3 days (twice per week)
- **Rationale**: Provides ~4 days of margin. Even if one ping fails, the next
  one fires before the 7-day deadline.

A cron schedule of `0 12 * * 1,4` (every Monday and Thursday at 12:00 UTC)
achieves this.

## Setup: Free External Ping Service

Since this project does not have a GitHub repository (no `.git` directory
exists), GitHub Actions scheduled workflows are not available. Instead, use
a free external uptime/cron service.

### Option A: cron-job.org (Recommended)

[cron-job.org](https://cron-job.org) — free tier includes unlimited cron
jobs with up to 1-minute granularity.

**Setup steps:**

1. Create a free account at https://cron-job.org/en/signup/
2. Click **"CREATE CRONJOB"**
3. Configure:
   - **Title**: `Legal E-Discovery Keep-Alive`
   - **URL**: `https://<YOUR_DEPLOYED_BACKEND_URL>/api/v1/health`
     - Replace `<YOUR_DEPLOYED_BACKEND_URL>` with the actual production
       backend URL (e.g., if deployed on Render, Railway, Fly.io, etc.)
     - For local-only development, this is not needed — the database only
       goes inactive when no one is using the app locally either
   - **Schedule**: Select "Every 3 days" or use custom cron: `0 12 */3 * *`
   - **Request method**: GET
   - **Request timeout**: 30 seconds
   - **Notification on failure**: Enable (enter your email)
4. Click **"CREATE"**

### Option B: UptimeRobot

[UptimeRobot](https://uptimerobot.com) — free tier includes 50 monitors
with 5-minute check intervals.

**Setup steps:**

1. Create a free account at https://uptimerobot.com/signUp
2. Click **"+ Add New Monitor"**
3. Configure:
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: `Legal E-Discovery Keep-Alive`
   - **URL**: `https://<YOUR_DEPLOYED_BACKEND_URL>/api/v1/health`
   - **Monitoring Interval**: 5 minutes (the free tier minimum; more
     frequent than needed, but ensures the database is always active)
4. Click **"Create Monitor"**

**Note**: UptimeRobot's minimum interval is 5 minutes. This is far more
frequent than needed for keep-alive (every 3 days would suffice), but on
the free tier you cannot set longer intervals. The extra pings add
negligible load since `SELECT 1` is extremely lightweight.

### Option C: Supabase pg_cron (No External Service Needed)

If you prefer to avoid external services entirely, Supabase includes
`pg_cron` for scheduling SQL jobs directly inside the database:

1. Open the Supabase Dashboard → **SQL Editor**
2. Run:
   ```sql
   -- Enable pg_cron if not already enabled
   CREATE EXTENSION IF NOT EXISTS pg_cron;

   -- Schedule a lightweight query every 3 days
   SELECT cron.schedule(
     'keep-alive-ping',
     '0 12 */3 * *',
     $$SELECT 1$$
   );
   ```
3. Verify it was created:
   ```sql
   SELECT * FROM cron.job;
   ```

**Advantage**: This runs entirely inside Supabase — no external account,
no deployed backend URL needed. The database pings itself.

**Note**: `pg_cron` is available on Supabase free tier but the extension
must be enabled first. If `CREATE EXTENSION pg_cron` fails with a
permissions error, use the Supabase Dashboard → **Database** →
**Extensions** page to enable it via the UI.

## How to Verify It's Working

### Manual verification
```bash
curl -s https://<YOUR_DEPLOYED_BACKEND_URL>/api/v1/health | python -m json.tool
```
Confirm `dependencies[0].status` is `"up"` (PostgreSQL is reachable and
the `SELECT 1` query succeeded).

### Service verification
- **cron-job.org**: Check the job's "History" tab for successful executions
- **UptimeRobot**: Check the monitor's uptime log
- **pg_cron**: Run `SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 5;`

### Supabase Dashboard
Visit your project at https://supabase.com/dashboard — if the project
shows as **"Active"** (green status), the keep-alive is working. If it
shows **"Paused"**, the ping is not reaching the database.
