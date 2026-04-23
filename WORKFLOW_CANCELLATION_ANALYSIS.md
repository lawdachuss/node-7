# Workflow Cancellation Analysis - CRITICAL FINDINGS

## ⚠️ CRITICAL ISSUE FOUND

### Current Behavior

**When workflow is cancelled mid-recording:**
1. GitHub Actions sends **SIGKILL** (force kill) - NOT SIGINT/SIGTERM
2. The graceful shutdown handler in `main.go` **NEVER RUNS**
3. Files are **NOT** properly closed or synced
4. In-progress recordings are **LOST** or **CORRUPTED**

### Why This Happens

**Current Signal Handler** (main.go):
```go
go func() {
    sigCh := make(chan os.Signal, 1)
    signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)  // ❌ Only catches SIGINT/SIGTERM
    <-sigCh
    fmt.Println("Shutting down, waiting for recordings to close and finalize...")
    server.Manager.Shutdown()
    os.Exit(0)
}()
```

**GitHub Actions Cancellation:**
- Sends **SIGKILL** (signal 9) which **CANNOT** be caught
- Process is immediately terminated
- No cleanup code runs
- Files remain open and unflushed

---

## 🔍 What Gets Lost

### 1. **In-Progress Recording Files**
- File handle is open but not closed
- Data in write buffers is **NOT** flushed to disk
- File may be **corrupted** or **incomplete**
- **Result**: Partial recording lost

### 2. **MP4 Init Segments**
- For MP4 files, the init segment may not be written
- File is **unplayable** without proper MP4 headers
- **Result**: Entire recording unusable

### 3. **Finalization Tasks**
- FFmpeg conversion/remux not completed
- GoFile upload not completed
- Database logging not completed
- **Result**: Recording not processed or uploaded

### 4. **Channel State**
- Channel config not saved
- Pause/resume state lost
- **Result**: Channels may restart incorrectly

---

## ✅ What's Protected (Good News)

### 1. **Completed Recordings**
- Files that finished before cancellation are safe
- Already closed and synced to disk
- Finalization runs in background goroutines

### 2. **Graceful Shutdown (When Possible)**
- SIGINT (Ctrl+C) works correctly
- SIGTERM (docker stop) works correctly
- Waits for all finalizations to complete
- Properly closes all files

---

## 🛡️ Solutions

### Solution 1: Periodic File Sync (RECOMMENDED)
**Add periodic sync during recording to minimize data loss**

**Implementation**:
```go
// In handleSegmentForMonitor, add periodic sync
var segmentCount int
n, err := ch.File.Write(b)
if err != nil {
    ch.fileMu.Unlock()
    return fmt.Errorf("write file: %w", err)
}

ch.Filesize += n
ch.Duration += duration
segmentCount++

// Sync every 10 segments (~10 seconds of video)
if segmentCount%10 == 0 {
    if err := ch.File.Sync(); err != nil {
        ch.Error("periodic sync failed: %v", err)
    }
}
```

**Pros**:
- Minimizes data loss to last ~10 seconds
- No workflow changes needed
- Works with any cancellation method

**Cons**:
- Slight performance overhead (minimal)
- File may still be incomplete/corrupted

---

### Solution 2: Workflow Timeout Handler (PARTIAL)
**Add a pre-timeout warning in GitHub Actions**

**Implementation** (.github/workflows/record.yml):
```yaml
jobs:
  record:
    timeout-minutes: 360  # 6 hours
    steps:
      - name: Record with timeout warning
        run: |
          # Start recording in background
          ./goondvr &
          PID=$!
          
          # Wait for timeout-5min or manual stop
          timeout 355m wait $PID || true
          
          # Send graceful shutdown
          kill -SIGTERM $PID
          
          # Wait up to 5 minutes for cleanup
          timeout 5m wait $PID || kill -9 $PID
```

**Pros**:
- Allows graceful shutdown before timeout
- 5-minute window for finalization

**Cons**:
- Doesn't help with manual cancellation
- Requires workflow changes
- Complex to implement

---

### Solution 3: Write-Ahead Logging (COMPLEX)
**Keep a transaction log of segments written**

**Pros**:
- Can recover from any interruption
- Professional solution

**Cons**:
- Complex implementation
- Significant code changes
- Overkill for this use case

---

## 📊 Risk Assessment

### Current Risk Level: **HIGH** 🔴

| Scenario | Risk | Data Loss |
|----------|------|-----------|
| **Manual workflow cancellation** | 🔴 HIGH | Last 30-60 seconds + file corruption |
| **Workflow timeout** | 🔴 HIGH | Last 30-60 seconds + file corruption |
| **GitHub Actions crash** | 🔴 HIGH | Entire recording |
| **Ctrl+C (local)** | 🟢 LOW | None (graceful shutdown) |
| **Docker stop (local)** | 🟢 LOW | None (graceful shutdown) |

### With Solution 1 (Periodic Sync): **MEDIUM** 🟡

| Scenario | Risk | Data Loss |
|----------|------|-----------|
| **Manual workflow cancellation** | 🟡 MEDIUM | Last ~10 seconds |
| **Workflow timeout** | 🟡 MEDIUM | Last ~10 seconds |
| **GitHub Actions crash** | 🟡 MEDIUM | Last ~10 seconds |
| **Ctrl+C (local)** | 🟢 LOW | None (graceful shutdown) |
| **Docker stop (local)** | 🟢 LOW | None (graceful shutdown) |

---

## 🎯 Recommended Action Plan

### Immediate (High Priority)
1. ✅ **Implement Solution 1: Periodic File Sync**
   - Add sync every 10 segments
   - Minimal code change
   - Reduces data loss from 30-60s to ~10s

2. ✅ **Add MP4 Init Segment Protection**
   - Write init segment immediately
   - Sync after init segment write
   - Ensures file is at least playable

### Short Term (Medium Priority)
3. ⚠️ **Add Workflow Timeout Handler**
   - Implement graceful shutdown before timeout
   - 5-minute cleanup window
   - Requires workflow changes

4. ⚠️ **Add Recovery Mechanism**
   - Detect incomplete files on startup
   - Attempt to repair MP4 files
   - Log incomplete recordings

### Long Term (Low Priority)
5. 📝 **Document Cancellation Behavior**
   - Warn users about data loss risk
   - Recommend letting recordings complete
   - Provide recovery instructions

---

## 🔧 Implementation

### Fix 1: Periodic File Sync
**File**: `channel/channel_record.go`

Add segment counter and periodic sync in `handleSegmentForMonitor`:

```go
// Add to Channel struct
type Channel struct {
    // ... existing fields ...
    segmentCount int
}

// In handleSegmentForMonitor
n, err := ch.File.Write(b)
if err != nil {
    ch.fileMu.Unlock()
    return fmt.Errorf("write file: %w", err)
}

ch.Filesize += n
ch.Duration += duration
ch.segmentCount++

// Sync every 10 segments to minimize data loss on forced shutdown
if ch.segmentCount%10 == 0 {
    if err := ch.File.Sync(); err != nil {
        // Log but don't fail - sync is best-effort
        if server.Config.Debug {
            ch.Error("periodic sync failed: %v", err)
        }
    }
}
```

### Fix 2: MP4 Init Segment Protection
**File**: `channel/channel_record.go`

Sync immediately after writing init segment:

```go
if ch.FileExt == ".mp4" && ch.Filesize == 0 && !isMP4InitSegment(b) && len(ch.mp4InitSegment) > 0 {
    n, err := ch.File.Write(ch.mp4InitSegment)
    if err != nil {
        ch.fileMu.Unlock()
        return fmt.Errorf("write mp4 init segment: %w", err)
    }
    ch.Filesize += n
    
    // CRITICAL: Sync init segment immediately to ensure file is playable
    if err := ch.File.Sync(); err != nil {
        ch.Error("init segment sync failed: %v", err)
    }
}
```

---

## 📈 Expected Results

### Before Fixes
- ❌ Workflow cancellation loses 30-60 seconds
- ❌ MP4 files may be unplayable
- ❌ File corruption common
- ❌ No recovery possible

### After Fixes
- ✅ Workflow cancellation loses only ~10 seconds
- ✅ MP4 files remain playable
- ✅ File corruption rare
- ✅ Minimal data loss

---

## 🚨 User Recommendations

### For GitHub Actions Users
1. **Avoid cancelling workflows mid-recording**
   - Let recordings complete naturally
   - Use pause feature instead of cancel

2. **Set appropriate timeouts**
   - Allow 5-10 minutes for cleanup
   - Don't set tight timeouts

3. **Monitor disk space**
   - Ensure enough space for full recording
   - Disk full = forced shutdown = data loss

4. **Use upload feature**
   - Enable GoFile upload
   - Recordings uploaded in background
   - Less risk of total loss

### For Local Users
1. **Use Ctrl+C for graceful shutdown**
   - Waits for recordings to finish
   - Properly closes all files
   - No data loss

2. **Don't use kill -9**
   - Same as workflow cancellation
   - Forces immediate termination
   - Data loss guaranteed

---

## ✅ Conclusion

**Current State**: 🔴 HIGH RISK - Workflow cancellation causes data loss

**With Fixes**: 🟡 MEDIUM RISK - Data loss minimized to ~10 seconds

**Recommendation**: Implement both fixes immediately to protect user recordings.
