## 🔍 Investigation Complete - Manual Diagnostics Required

**Status**: Comprehensive troubleshooting tools created
**Branch**: `claude/project-summary-review-011CUR83MwFXH1cs8JXAcTdd`
**Commits**: 3a21498

---

## 📦 What Was Created

### **1. Automated Diagnostic Script** (`scripts/diagnose_schedule_workers.py`)
- Tests 8 different system components
- Identifies specific failure points
- Provides actionable error messages
- Can run locally or in production pods

### **2. Comprehensive Troubleshooting Guide** (`docs/TROUBLESHOOTING_106.md`)
- 6 potential root causes identified (ordered by probability)
- Detailed SQL queries for each diagnosis
- Step-by-step troubleshooting procedures
- Quick fix recommendations
- 400+ lines of detailed documentation

### **3. Quick Reference Summary** (`INVESTIGATION_106.md`)
- Executive summary of findings
- Manual steps required
- Expected diagnostic output examples

---

## 🎯 Top 6 Root Cause Candidates

Based on code analysis, ordered by probability:

### **1. No Parishes Being Selected** (Highest Probability)
- `get_parishes_to_process()` returning empty list
- Intelligent prioritizer failing
- All parishes already have schedule data
- Invalid/NULL Web URLs

### **2. All Parishes Being Blocked**
- Every website returns blocking errors (Cloudflare, 403)
- IP address blacklisted
- Aggressive bot detection

### **3. Monitoring Client Communication Issues**
- Workers running but not reporting results
- Backend unreachable
- Network policies blocking communication

### **4. Distributed Coordinator Not Assigning Work**
- Schedule workers registered but getting no assignments
- Dioceses stuck in "processing" status
- Worker type filtering issues

### **5. AI Extractor Failing**
- Google Gemini API calls failing
- API key invalid or quota exceeded
- Network timeouts

### **6. Schedule-Specific Worker Type Issues**
- Only schedule workers failing (other types OK)
- Worker type environment variable misconfigured
- Schedule extraction logic bugs

---

## 🚀 Next Steps (Manual Execution Required)

### **Step 1: Run Diagnostic Script** (5 minutes)

**Option A: Run Locally**
```bash
cd /home/user/diocesan-vitality
source .venv/bin/activate
python3 scripts/diagnose_schedule_workers.py
```

**Option B: Run in Production Pod**
```bash
# Copy script to pod
kubectl cp scripts/diagnose_schedule_workers.py \
  diocesan-vitality-prd/pipeline-deployment-xxx:/tmp/

# Execute diagnostic
kubectl exec -n diocesan-vitality-prd deployment/pipeline-deployment -- \
  python3 /tmp/diagnose_schedule_workers.py
```

**Expected Output:**
```
📊 Test 1: Database Connection
✅ Database connection successful

📊 Test 2: Parishes with Websites
✅ Total parishes with websites: 17,234

📊 Test 3: Parishes Without Schedule Data
⚠️  Parishes WITHOUT schedule data: 16,811

📊 Test 7: Parish Selection Logic
❌ CRITICAL: Parish selection returned 0 parishes!
   This would cause 0% success rate
```

---

### **Step 2: Check Production Logs** (2 minutes)

```bash
# Get recent pipeline logs
kubectl logs -n diocesan-vitality-prd deployment/pipeline-deployment \
  --tail=500 > pipeline_logs.txt

# Search for errors
grep -i "schedule\|step 4\|error\|failed" pipeline_logs.txt

# Check worker registration
grep -i "worker.*registered\|worker type" pipeline_logs.txt
```

---

### **Step 3: Run Database Diagnostics** (3 minutes)

Open Supabase SQL Editor: https://supabase.com/dashboard/project/nzcwtjloonumxpsqzarq/sql

**Query 1: Parishes Available for Processing**
```sql
SELECT COUNT(*) as parishes_without_schedules
FROM "Parishes" p
LEFT JOIN "ParishData" pd ON p.id = pd.parish_id
WHERE p."Web" IS NOT NULL
  AND p."Web" != ''
  AND pd.id IS NULL;
```

**Query 2: Blocking Statistics**
```sql
SELECT
  is_blocked,
  blocking_type,
  COUNT(*) as count
FROM "Parishes"
WHERE "Web" IS NOT NULL
GROUP BY is_blocked, blocking_type
ORDER BY count DESC;
```

**Query 3: Active Workers**
```sql
SELECT
  worker_id,
  worker_type,
  status,
  last_heartbeat,
  NOW() - last_heartbeat as inactive_duration
FROM pipeline_workers
WHERE status = 'active'
ORDER BY last_heartbeat DESC;
```

**Query 4: Stuck Work Assignments**
```sql
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

**Query 5: Recent Schedule Extractions**
```sql
SELECT
  pd.id,
  pd.parish_id,
  pd.fact_type,
  pd.created_at,
  pd.confidence_score,
  p."Name" as parish_name
FROM "ParishData" pd
JOIN "Parishes" p ON p.id = pd.parish_id
WHERE pd.created_at > NOW() - INTERVAL '7 days'
  AND pd.fact_type IN ('ReconciliationSchedule', 'AdorationSchedule')
ORDER BY pd.created_at DESC
LIMIT 20;
```

---

### **Step 4: Test Single Parish Extraction** (Optional, 5 minutes)

```bash
# Find a test parish
python3 -c "
from core.db import get_supabase_client
supabase = get_supabase_client()
parish = supabase.table('Parishes').select('id, Name, Web').not_.is_('Web', 'null').limit(1).execute()
if parish.data:
    p = parish.data[0]
    print(f'Test Parish: ID={p[\"id\"]}, Name={p[\"Name\"]}, Web={p[\"Web\"]}')
"

# Run schedule extraction on that parish
python3 -m pipeline.extract_schedule_respectful --parish_id <ID_FROM_ABOVE>

# Check output for errors or success
```

---

## 🔧 Quick Fixes (Apply Based on Diagnostic Results)

### **If "Stuck Work Assignments" Found:**
```sql
-- Reset assignments stuck in processing > 2 hours
UPDATE diocese_work_assignments
SET status = 'failed',
    completed_at = NOW()
WHERE status = 'processing'
  AND NOW() - assigned_at > INTERVAL '2 hours';
```

### **If "Inactive Workers" Found:**
```sql
-- Mark workers as inactive (no heartbeat in 10 minutes)
UPDATE pipeline_workers
SET status = 'inactive'
WHERE status = 'active'
  AND NOW() - last_heartbeat > INTERVAL '10 minutes';
```

### **If "Parish Selection Returns 0":**
May need to debug or temporarily disable `intelligent_parish_prioritizer` logic.

---

## 📊 What to Report Back

After running diagnostics, please comment here with:

1. **Diagnostic script output** (especially any ❌ CRITICAL errors)
2. **Database query results** (parish counts, blocking stats, worker status)
3. **Production log snippets** (any relevant errors)
4. **Single parish test results** (if you ran step 4)

---

## 📚 Complete Documentation

- **Quick Reference**: `INVESTIGATION_106.md`
- **Full Troubleshooting Guide**: `docs/TROUBLESHOOTING_106.md` (400+ lines)
- **Diagnostic Script**: `scripts/diagnose_schedule_workers.py`

---

## ⏱️ Estimated Time

- **Running diagnostics**: 10-15 minutes
- **Analyzing results**: 5-10 minutes
- **Applying fixes**: 5-30 minutes (depends on root cause)
- **Total**: 20-55 minutes

---

## 🎯 Success Criteria

Once root cause is identified and fixed, verify:
- ✅ Diagnostic script shows no CRITICAL errors
- ✅ Parish selection returns > 0 parishes
- ✅ Single parish extraction succeeds
- ✅ Schedule workers appear in monitoring dashboard
- ✅ ParishData table shows new records being added
- ✅ Success rate > 0% (ideally > 50%)

---

🤖 *Generated with [Claude Code](https://claude.com/claude-code)*
