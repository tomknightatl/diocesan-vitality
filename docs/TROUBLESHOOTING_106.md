# Troubleshooting Issue #106 - Schedule Workers Near 0% Success

**Issue**: Schedule Workers showing ~0% success rate
**Created**: September 15, 2025
**Priority**: 🚨 CRITICAL - Core pipeline functionality
**Status**: 🔍 Investigation In Progress

---

## 📋 **Problem Summary**

The Schedule Workers (Step 4 of the pipeline) are reporting near 0% success rate when attempting to extract mass schedules from parish websites. This is a critical production issue affecting the core data collection functionality.

---

## 🔍 **Initial Analysis**

### **System Architecture**

The schedule extraction system uses:
- **Primary Script**: `pipeline/extract_schedule_respectful.py` (483 lines)
- **Fallback Script**: `pipeline/extract_schedule.py` (1,452 lines)
- **Caller**: `pipeline/distributed_pipeline_runner.py` (Schedule workers)
- **AI Extractor**: `core/schedule_ai_extractor.py`
- **Respectful Automation**: `pipeline/respectful_automation.py`

### **Call Flow**

```
distributed_pipeline_runner.py
  ├─> extract_schedule_respectful.main()
  │     ├─> get_parishes_to_process()
  │     │     └─> intelligent_parish_prioritizer.get_prioritized_parishes()
  │     ├─> RespectfulAutomation.respectful_get()
  │     ├─> extract_content_with_respectful_automation()
  │     └─> ScheduleAIExtractor.extract_schedule_from_content()
  └─> monitoring_client.send_log()
```

---

## 🎯 **Potential Root Causes**

### **1. No Parishes Being Selected (Most Likely)**

**Symptoms:**
- Workers start but process 0 parishes
- Logs show "No parishes to process"
- `get_parishes_to_process()` returns empty list

**Possible Causes:**
- Intelligent prioritizer failing and returning empty results
- All parishes already have schedule data extracted
- Diocese filtering excluding all parishes
- Invalid or NULL Web URLs in database

**How to Check:**
```sql
-- Check total parishes with websites
SELECT COUNT(*) as total_parishes_with_websites
FROM "Parishes"
WHERE "Web" IS NOT NULL AND "Web" != '';

-- Check parishes without schedule data
SELECT COUNT(*) as parishes_without_schedules
FROM "Parishes" p
LEFT JOIN "ParishData" pd ON p.id = pd.parish_id
WHERE p."Web" IS NOT NULL
  AND p."Web" != ''
  AND pd.id IS NULL;

-- Check intelligent prioritizer results
-- This would need to be run in Python context
```

---

### **2. All Parishes Being Blocked**

**Symptoms:**
- Parishes selected but all return blocking errors
- Logs show "🚫 Website is blocking access"
- Success rate = 0%

**Possible Causes:**
- Too many parishes behind Cloudflare protection
- IP address blacklisted
- User-agent detection
- robots.txt disallowing access

**How to Check:**
```sql
-- Check blocking statistics
SELECT
  is_blocked,
  blocking_type,
  COUNT(*) as count
FROM "Parishes"
WHERE "Web" IS NOT NULL
GROUP BY is_blocked, blocking_type
ORDER BY count DESC;

-- Check recent blocking attempts
SELECT
  blocking_type,
  status_description,
  COUNT(*) as count
FROM "Parishes"
WHERE extracted_at > NOW() - INTERVAL '7 days'
GROUP BY blocking_type, status_description
ORDER BY count DESC;
```

---

### **3. Monitoring Client Communication Issues**

**Symptoms:**
- Workers running but no logs appearing in dashboard
- Success happening but not being reported
- `monitoring_client` is None or not working

**Possible Causes:**
- Backend service unreachable
- `monitoring_url` incorrect
- Network policy blocking communication
- Monitoring disabled in worker configuration

**How to Check:**
```bash
# Check if backend is reachable from pipeline pods
kubectl exec -n diocesan-vitality-prd deployment/pipeline-deployment -- curl -v http://backend-service:8000/api

# Check pipeline pod logs for monitoring errors
kubectl logs -n diocesan-vitality-prd deployment/pipeline-deployment --tail=100 | grep -i "monitoring\|error"

# Check environment variables
kubectl exec -n diocesan-vitality-prd deployment/pipeline-deployment -- env | grep MONITORING
```

---

### **4. Distributed Coordinator Not Assigning Work**

**Symptoms:**
- Schedule workers registered but idle
- Logs show "⏸️ No work available"
- Other worker types processing normally

**Possible Causes:**
- Work assignment logic excluding schedule tasks
- Diocese already claimed by other workers
- Worker type filtering issues
- Database coordination table issues

**How to Check:**
```sql
-- Check active workers
SELECT
  worker_id,
  worker_type,
  status,
  last_heartbeat,
  assigned_dioceses
FROM pipeline_workers
WHERE status = 'active'
ORDER BY last_heartbeat DESC;

-- Check work assignments
SELECT
  diocese_id,
  worker_id,
  status,
  assigned_at,
  completed_at
FROM diocese_work_assignments
WHERE status IN ('processing', 'failed')
ORDER BY assigned_at DESC
LIMIT 20;

-- Check if dioceses are stuck in processing
SELECT
  d."Name" as diocese_name,
  dwa.worker_id,
  dwa.status,
  dwa.assigned_at,
  NOW() - dwa.assigned_at as processing_duration
FROM diocese_work_assignments dwa
JOIN "Dioceses" d ON d.id = dwa.diocese_id
WHERE dwa.status = 'processing'
  AND NOW() - dwa.assigned_at > INTERVAL '1 hour'
ORDER BY processing_duration DESC;
```

---

### **5. AI Extractor Failing**

**Symptoms:**
- Parishes selected and accessed
- Content extracted successfully
- AI extraction returns no results or errors

**Possible Causes:**
- Google Gemini API key invalid or quota exceeded
- AI model returning low confidence results
- Content not matching expected patterns
- Network timeout calling AI API

**How to Check:**
```bash
# Check for AI-related errors in logs
kubectl logs -n diocesan-vitality-prd deployment/pipeline-deployment --tail=500 | grep -i "gemini\|ai\|genai"

# Check environment variable
kubectl exec -n diocesan-vitality-prd deployment/pipeline-deployment -- env | grep GENAI_API_KEY
```

---

### **6. Schedule-Specific Worker Type Issues**

**Symptoms:**
- Discovery and extraction workers successful
- Only schedule workers at 0%
- Worker type filtering preventing schedule work

**Possible Causes:**
- `distributed_pipeline_runner.py` not calling schedule extraction properly
- Worker type environment variable misconfigured
- Schedule worker logic has bugs

**How to Check:**
```bash
# Check worker type configuration
kubectl get deployment -n diocesan-vitality-prd pipeline-deployment -o yaml | grep -A 5 WORKER_TYPE

# Check if schedule extraction is being called
kubectl logs -n diocesan-vitality-prd deployment/pipeline-deployment --tail=1000 | grep "Step 4\|extract_schedule"
```

---

## 🔧 **Troubleshooting Steps**

### **Step 1: Check Pod and Worker Status**

```bash
# Check if pipeline pods are running
kubectl get pods -n diocesan-vitality-prd -l app=pipeline

# Check pod logs for errors
kubectl logs -n diocesan-vitality-prd deployment/pipeline-deployment --tail=200

# Check for crash loops or restarts
kubectl describe pod -n diocesan-vitality-prd -l app=pipeline | grep -A 5 "Restart Count\|Last State"
```

### **Step 2: Verify Database Connectivity**

```bash
# Test database connection from pipeline pod
kubectl exec -n diocesan-vitality-prd deployment/pipeline-deployment -- python3 -c "
from core.db import get_supabase_client
supabase = get_supabase_client()
if supabase:
    result = supabase.table('Parishes').select('id').limit(1).execute()
    print(f'✅ Database connection successful: {len(result.data)} records')
else:
    print('❌ Database connection failed')
"
```

### **Step 3: Test Schedule Extraction Locally**

```bash
# Run schedule extraction for a single parish locally
python3 -m pipeline.extract_schedule_respectful \
  --parish_id 1 \
  --max_pages_per_parish 5

# Check output for errors or success
```

### **Step 4: Check Monitoring Dashboard**

```bash
# Access monitoring dashboard
open https://ui.diocesanvitality.org/dashboard

# Check for:
# - Schedule workers appearing in active workers list
# - Recent logs from schedule workers
# - Error messages in dashboard logs
# - Last successful schedule extraction timestamp
```

### **Step 5: Review Recent Code Changes**

```bash
# Check recent commits affecting schedule extraction
git log --oneline --since="2025-09-01" -- pipeline/extract_schedule* core/schedule*

# Review issue #163 commits (monitoring integration)
git log --grep="#163" --oneline
```

---

## 🐛 **Known Issues & Recent Changes**

### **Issue #163 - Monitoring Integration**

Recent commits related to monitoring support:
- `0b5d360` - ✨ Add monitoring support to extract_schedule_respectful.py
- `33d6fa1` - 🐛 Fix parish info database query in schedule worker
- `46aba73` - 🐛 Add debug logging for monitoring_client parameter
- `bb57a96` - 🐛 Add detailed debug logging for monitoring message flow
- `7ea10ac` - 🧹 Remove debug logging

**Potential Issue**: Monitoring client integration may have introduced bugs affecting schedule extraction success reporting.

**Action**: Review these commits for unintended side effects.

---

## ✅ **Quick Diagnostic Script**

Run this comprehensive diagnostic:

```python
#!/usr/bin/env python3
"""
Quick diagnostic for schedule worker issues.
Run from project root: python3 scripts/diagnose_schedule_workers.py
"""

from core.db import get_supabase_client
from core.logger import get_logger

logger = get_logger(__name__)

def diagnose_schedule_workers():
    """Run comprehensive diagnostics on schedule workers."""

    supabase = get_supabase_client()
    if not supabase:
        logger.error("❌ Cannot connect to database")
        return

    logger.info("✅ Database connection successful")

    # 1. Check parishes with websites
    parishes_response = (
        supabase.table("Parishes")
        .select("id", count="exact")
        .not_.is_("Web", "null")
        .execute()
    )
    logger.info(f"📊 Total parishes with websites: {parishes_response.count}")

    # 2. Check parishes without schedule data
    parishes_without_data = (
        supabase.table("Parishes")
        .select("id", count="exact")
        .not_.is_("Web", "null")
        .is_("id", "null")  # Not in ParishData
        .execute()
    )
    logger.info(f"📊 Parishes without schedule data: {parishes_without_data.count}")

    # 3. Check blocking statistics
    blocking_stats = (
        supabase.table("Parishes")
        .select("is_blocked, blocking_type, COUNT(*)")
        .not_.is_("Web", "null")
        .execute()
    )
    logger.info(f"📊 Blocking statistics: {blocking_stats.data}")

    # 4. Check active workers
    workers = (
        supabase.table("pipeline_workers")
        .select("*")
        .eq("status", "active")
        .execute()
    )
    logger.info(f"📊 Active workers: {len(workers.data)}")
    for worker in workers.data:
        logger.info(f"  - {worker['worker_id']} ({worker['worker_type']}) - Last heartbeat: {worker['last_heartbeat']}")

    # 5. Check ParishData records added recently
    recent_data = (
        supabase.table("ParishData")
        .select("*", count="exact")
        .gte("created_at", "2025-09-01")
        .execute()
    )
    logger.info(f"📊 Parish data records since Sept 1: {recent_data.count}")

    # 6. Test parish selection
    from pipeline.extract_schedule import get_parishes_to_process
    test_parishes = get_parishes_to_process(supabase, num_parishes=10)
    logger.info(f"📊 Test parish selection returned: {len(test_parishes)} parishes")
    if test_parishes:
        logger.info(f"  Sample: {test_parishes[:3]}")

    logger.info("\n" + "="*60)
    logger.info("Diagnostic complete. Check output above for issues.")
    logger.info("="*60)

if __name__ == "__main__":
    diagnose_schedule_workers()
```

Save this as `scripts/diagnose_schedule_workers.py` and run it.

---

## 🔨 **Potential Fixes**

### **Fix 1: Reset Stuck Work Assignments**

If dioceses are stuck in "processing" status:

```sql
-- Find stuck assignments (processing for > 2 hours)
SELECT
  id,
  diocese_id,
  worker_id,
  status,
  assigned_at,
  NOW() - assigned_at as stuck_duration
FROM diocese_work_assignments
WHERE status = 'processing'
  AND NOW() - assigned_at > INTERVAL '2 hours';

-- Reset them (CAUTION: Only if workers are truly dead)
UPDATE diocese_work_assignments
SET status = 'failed',
    completed_at = NOW()
WHERE status = 'processing'
  AND NOW() - assigned_at > INTERVAL '2 hours';
```

### **Fix 2: Clear Inactive Workers**

If workers are registered but not sending heartbeats:

```sql
-- Find inactive workers (no heartbeat in 10 minutes)
SELECT
  worker_id,
  worker_type,
  status,
  last_heartbeat,
  NOW() - last_heartbeat as inactive_duration
FROM pipeline_workers
WHERE status = 'active'
  AND NOW() - last_heartbeat > INTERVAL '10 minutes';

-- Mark them as inactive
UPDATE pipeline_workers
SET status = 'inactive'
WHERE status = 'active'
  AND NOW() - last_heartbeat > INTERVAL '10 minutes';
```

### **Fix 3: Enable Debug Logging**

Temporarily add debug logging to schedule extraction:

```python
# In pipeline/extract_schedule_respectful.py, add at start of main():
logger.setLevel(logging.DEBUG)
logger.debug(f"📝 Schedule extraction called with: num_parishes={num_parishes}, parish_id={parish_id}, diocese_id={diocese_id}")
logger.debug(f"📝 Monitoring client: {monitoring_client}")
```

### **Fix 4: Test Single Parish Extraction**

Run a controlled test on one parish:

```bash
# Find a parish with a website
python3 -c "
from core.db import get_supabase_client
supabase = get_supabase_client()
parish = supabase.table('Parishes').select('id, Name, Web').not_.is_('Web', 'null').limit(1).execute()
if parish.data:
    p = parish.data[0]
    print(f'Test parish: ID={p[\"id\"]}, Name={p[\"Name\"]}, Web={p[\"Web\"]}')
"

# Run extraction on that parish
python3 -m pipeline.extract_schedule_respectful --parish_id <ID_FROM_ABOVE>
```

---

## 📊 **Success Metrics**

To verify fix effectiveness, track:

1. **Parish Selection Rate**: % of parishes selected for processing
2. **Access Success Rate**: % of parishes successfully accessed (not blocked)
3. **Content Extraction Rate**: % of accessed parishes with content extracted
4. **AI Success Rate**: % of content successfully analyzed by AI
5. **Schedule Found Rate**: % of parishes where schedules were found
6. **Overall Success Rate**: End-to-end success (schedules found / parishes selected)

---

## 📝 **Next Steps**

1. **Run diagnostic script** to identify specific failure point
2. **Review recent logs** from production pipeline pods
3. **Test locally** with single parish to isolate issue
4. **Check monitoring dashboard** for worker activity
5. **Review database** for stuck work assignments
6. **Verify AI API** keys and quotas
7. **Test network connectivity** between pods

---

## 🚀 **Resolution Plan**

Once root cause is identified:

1. Create fix (code change, configuration, or database cleanup)
2. Test fix locally with sample parishes
3. Deploy fix to development cluster first
4. Monitor success rate improvements
5. Deploy to staging, then production
6. Document resolution in this issue
7. Update monitoring to prevent recurrence

---

**Last Updated**: 2025-10-24
**Status**: Ready for troubleshooting
**Owner**: Needs assignment
