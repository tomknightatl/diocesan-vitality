# 🔍 Issue #106 Investigation Summary

**Issue**: Schedule Workers - Troubleshoot why success near 0%
**Status**: Investigation Complete - Ready for Manual Troubleshooting
**Priority**: 🚨 CRITICAL
**Created**: 2025-10-24

---

## ✅ **Investigation Complete**

I've analyzed the schedule worker codebase and created comprehensive troubleshooting tools for Issue #106.

---

## 📦 **Files Created**

### **1. Troubleshooting Guide** (`docs/TROUBLESHOOTING_106.md`)
- 6 potential root causes identified
- Detailed SQL queries for each diagnosis
- Step-by-step troubleshooting procedures
- Quick diagnostic script included
- Fix recommendations for common issues

### **2. Diagnostic Script** (`scripts/diagnose_schedule_workers.py`)
- Automated diagnostic checks
- Tests 8 different potential failure points
- Provides actionable error messages
- Can be run locally or in production pods

---

## 🎯 **Top 6 Potential Root Causes**

Based on code analysis, here are the most likely causes (ordered by probability):

### **1. No Parishes Being Selected** (Highest Probability)
- **What**: `get_parishes_to_process()` returns empty list
- **Why**: Intelligent prioritizer failing, all parishes already processed, or invalid URLs
- **Impact**: 0% success because nothing to process
- **Check**: Run diagnostic script, check database for parishes without schedule data

### **2. All Parishes Being Blocked**
- **What**: Every parish website returns blocking errors (Cloudflare, 403, etc.)
- **Why**: IP blacklisting, aggressive bot detection, robots.txt
- **Impact**: 0% success because can't access any websites
- **Check**: Query `Parishes` table for `is_blocked=true` statistics

### **3. Monitoring Client Communication Issues**
- **What**: Workers running but not reporting results
- **Why**: Backend unreachable, monitoring disabled, network policy
- **Impact**: Appears as 0% but may actually be working
- **Check**: Pod logs, backend connectivity, monitoring URL configuration

### **4. Distributed Coordinator Not Assigning Work**
- **What**: Schedule workers registered but getting no work assignments
- **Why**: Diocese already claimed, worker type filtering, stuck assignments
- **Impact**: Workers idle, no processing happens
- **Check**: `diocese_work_assignments` and `pipeline_workers` tables

### **5. AI Extractor Failing**
- **What**: Google Gemini API calls failing or returning no results
- **Why**: Invalid API key, quota exceeded, network timeout
- **Impact**: Content extracted but no schedules found
- **Check**: Pod logs for "gemini" or "ai" errors, API key validity

### **6. Schedule-Specific Worker Type Issues**
- **What**: Only schedule workers failing, other worker types successful
- **Why**: Worker type environment variable misconfigured, schedule logic bug
- **Impact**: Other pipeline steps work, only Step 4 fails
- **Check**: Worker type configuration in deployment

---

## 🚀 **Manual Steps Required**

Since I cannot directly access your production environment, **you need to run these diagnostics**:

### **Step 1: Run Diagnostic Script (5 minutes)**

**Option A: Locally**
```bash
# From project root
cd /home/user/diocesan-vitality
source .venv/bin/activate
python3 scripts/diagnose_schedule_workers.py
```

**Option B: In Production Pod**
```bash
# Copy script to pod and run
kubectl cp scripts/diagnose_schedule_workers.py \
  diocesan-vitality-prd/pipeline-deployment-xxx:/tmp/

kubectl exec -n diocesan-vitality-prd deployment/pipeline-deployment -- \
  python3 /tmp/diagnose_schedule_workers.py
```

### **Step 2: Check Production Logs (2 minutes)**

```bash
# Get recent pipeline logs
kubectl logs -n diocesan-vitality-prd deployment/pipeline-deployment \
  --tail=500 > pipeline_logs.txt

# Search for schedule-related errors
grep -i "schedule\|step 4\|error\|failed" pipeline_logs.txt

# Check for worker registration
grep -i "worker.*registered\|worker type" pipeline_logs.txt
```

### **Step 3: Query Database (3 minutes)**

Run these SQL queries in Supabase dashboard:

```sql
-- Query 1: Parishes available for processing
SELECT COUNT(*) as parishes_without_schedules
FROM "Parishes" p
LEFT JOIN "ParishData" pd ON p.id = pd.parish_id
WHERE p."Web" IS NOT NULL
  AND p."Web" != ''
  AND pd.id IS NULL;

-- Query 2: Blocking statistics
SELECT
  is_blocked,
  blocking_type,
  COUNT(*) as count
FROM "Parishes"
WHERE "Web" IS NOT NULL
GROUP BY is_blocked, blocking_type
ORDER BY count DESC;

-- Query 3: Active workers
SELECT
  worker_id,
  worker_type,
  status,
  last_heartbeat
FROM pipeline_workers
WHERE status = 'active'
ORDER BY last_heartbeat DESC;

-- Query 4: Stuck work assignments
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

### **Step 4: Test Single Parish (Optional)**

```bash
# Find a parish ID
python3 -c "from core.db import get_supabase_client; supabase = get_supabase_client(); parish = supabase.table('Parishes').select('id, Name, Web').not_.is_('Web', 'null').limit(1).execute(); print(f'Test ID: {parish.data[0][\"id\"]}')"

# Run extraction on that parish
python3 -m pipeline.extract_schedule_respectful --parish_id <ID_FROM_ABOVE>
```

---

## 📊 **Expected Diagnostic Output**

The diagnostic script will tell you:

✅ **If all checks pass**: Issue may be with monitoring/reporting, not actual extraction
❌ **If specific check fails**: Pinpoints exact root cause
⚠️ **Warnings**: Contributing factors that reduce success rate

Example output:
```
📊 Test 1: Database Connection
✅ Database connection successful

📊 Test 2: Parishes with Websites
✅ Total parishes with websites: 17,234

📊 Test 3: Parishes Without Schedule Data
✅ Parishes WITH schedule data: 423
⚠️  Parishes WITHOUT schedule data: 16,811

📊 Test 7: Parish Selection Logic
❌ CRITICAL: Parish selection returned 0 parishes!
   This would cause 0% success rate
   Check intelligent_parish_prioritizer logic
```

---

## 🔧 **Quick Fixes (If Applicable)**

Based on diagnostic results, you may need to:

### **If "Stuck Work Assignments" Found:**
```sql
UPDATE diocese_work_assignments
SET status = 'failed',
    completed_at = NOW()
WHERE status = 'processing'
  AND NOW() - assigned_at > INTERVAL '2 hours';
```

### **If "Inactive Workers" Found:**
```sql
UPDATE pipeline_workers
SET status = 'inactive'
WHERE status = 'active'
  AND NOW() - last_heartbeat > INTERVAL '10 minutes';
```

### **If "Parish Selection Returns 0":**
Check `core/intelligent_parish_prioritizer.py` for bugs or temporary disable it.

---

## 📚 **Complete Documentation**

- **Full Guide**: `docs/TROUBLESHOOTING_106.md` (comprehensive, 400+ lines)
- **Diagnostic Script**: `scripts/diagnose_schedule_workers.py` (automated checks)
- **This Summary**: `INVESTIGATION_106.md` (quick reference)

---

## 🎯 **Next Actions**

1. ✅ **Run diagnostic script** (locally or in production pod)
2. ✅ **Review output** for CRITICAL errors and warnings
3. ✅ **Check production logs** for detailed error messages
4. ✅ **Run SQL queries** to verify database state
5. ✅ **Apply quick fixes** if applicable
6. ✅ **Report findings** in GitHub issue #106
7. ✅ **Create fix PR** once root cause identified

---

## 📞 **Status**

**Investigation**: ✅ Complete
**Root Cause**: ⏳ Awaiting manual diagnostic results
**Fix**: ⏳ Pending root cause identification
**Testing**: ⏳ Pending fix implementation

---

🤖 *Generated with [Claude Code](https://claude.com/claude-code)*
