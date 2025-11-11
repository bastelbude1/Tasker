# Instance Control Manual Test Cases

These test cases require multi-process execution or system-level manipulation that cannot be automated in the single-process test harness. They should be tested manually before major releases.

## 1. Race Condition Test (Concurrent Lock Attempts)

**Purpose**: Verify that two near-simultaneous lock acquisition attempts don't both succeed.

**Setup**:
```bash
# Create test file
cat > /tmp/race_test.txt << 'EOF'
--instance-check

task=0
hostname=localhost
exec=local
command=sleep
arguments=5
EOF
```

**Test**:
```bash
# Start first instance in background
tasker -r /tmp/race_test.txt &
PID1=$!

# Immediately start second instance (within milliseconds)
sleep 0.01
tasker -r /tmp/race_test.txt
EXIT_CODE=$?

# Verify
echo "Exit code should be 25 (INSTANCE_ALREADY_RUNNING): $EXIT_CODE"
wait $PID1
```

**Expected**:
- First instance: Runs successfully (exit 0)
- Second instance: Blocked immediately (exit 25)
- Lock file contains PID of first instance

---

## 2. Stale Lock with PID Reuse

**Purpose**: Verify that stale locks are properly detected even if PID is reused.

**Setup**:
```bash
# This is very hard to test reliably because:
# - PID reuse is controlled by the kernel
# - We can't easily force a specific PID to be reused
# - Modern systems use large PID spaces (32768+)
```

**Current Limitation**:
- Our stale detection uses `os.kill(pid, 0)` which only checks if PID exists
- If PID is reused by another process, we'll think the lock is active
- **Future Enhancement**: Check if process name matches "tasker" or "python.*tasker"

**Manual Verification**:
1. Create lock file with PID of unrelated process (e.g., init)
2. Try to acquire lock
3. Should be blocked (current behavior)
4. Kill that process
5. Try again - should succeed

---

## 3. Symlink Attack Test

**Purpose**: Verify TASKER doesn't follow symlinks that could redirect lock writes.

**Setup**:
```bash
# Create symlink in locks directory pointing to sensitive file
mkdir -p ~/TASKER/locks
ln -s /etc/passwd ~/TASKER/locks/workflow_malicious123.lock
```

**Test**:
```bash
# Try to create a workflow with that specific hash (very hard)
# Current protection: Locks directory uses 0700 permissions
# Only owner can create symlinks there
```

**Current Protection**:
- Lock directory: 0700 (owner only)
- Lock files: 0600 (owner only)
- No special symlink protection implemented

**Recommendation**: Add `O_NOFOLLOW` flag to `os.open()` call in future enhancement.

---

## 4. Disk Full During Lock Write

**Purpose**: Verify graceful failure when disk is full.

**Setup**:
```bash
# This requires actually filling the disk or using quota limits
# Not practical for automated testing
```

**Manual Test**:
```bash
# On test system with limited space
dd if=/dev/zero of=~/TASKER/bigfile bs=1M count=<size-to-fill-disk>
tasker -r task.txt --instance-check
rm ~/TASKER/bigfile
```

**Expected**:
- Clear error message about disk full
- Exit with error code (not 0)
- No corrupted lock file left behind

**Current Behavior**: Untested - likely throws IOError/OSError

---

## 5. Corrupted Lock File (Automated Test Available)

**Purpose**: Verify TASKER handles corrupted lock JSON gracefully.

**Automated Test**: `test_instance_control_corrupted_lock.txt`

**Manual Verification**:
```bash
# Create workflow hash by running once
tasker -r /tmp/test.txt --instance-check
HASH=$(ls ~/TASKER/locks/ | grep workflow | sed 's/workflow_//' | sed 's/.lock//')

# Stop it with Ctrl+C

# Corrupt the lock file
echo "invalid json {{{" > ~/TASKER/locks/workflow_${HASH}.lock

# Try again - should detect corruption and overwrite
tasker -r /tmp/test.txt --instance-check --debug 2>&1 | grep -i corrupt
```

**Expected**:
- Detects corrupted JSON
- Logs: "# Overwriting corrupted lock file"
- Successfully acquires lock and runs

---

## 6. Missing Lock Directory

**Purpose**: Verify TASKER handles missing/deleted lock directory.

**Test**:
```bash
# This would require deleting directory while TASKER is running
# Which requires multi-process coordination

# What we CAN test:
rm -rf ~/TASKER/locks
tasker -r task.txt --instance-check
```

**Expected**:
- Creates `~/TASKER/locks/` automatically (0700)
- Continues normally

**Current Implementation**: ✅ Tested - `os.makedirs(locks_dir, mode=0o700, exist_ok=True)`

---

## 7. Multiple Different Workflows (Parallel Execution)

**Purpose**: Verify different workflows can run concurrently.

**Test**:
```bash
# Create two different task files
cat > /tmp/task1.txt << 'EOF'
--instance-check
task=0
hostname=localhost
exec=local
command=sleep
arguments=5
EOF

cat > /tmp/task2.txt << 'EOF'
--instance-check
task=0
hostname=localhost
exec=local
command=sleep
arguments=5
EOF

# Start both in background
tasker -r /tmp/task1.txt &
PID1=$!
tasker -r /tmp/task2.txt &
PID2=$!

# Both should succeed
wait $PID1
EXIT1=$?
wait $PID2
EXIT2=$?

echo "Task1 exit: $EXIT1 (should be 0)"
echo "Task2 exit: $EXIT2 (should be 0)"

# Verify different lock files created
ls -la ~/TASKER/locks/
```

**Expected**:
- Both workflows run successfully
- Two different lock files created (different hashes)
- No interference between workflows

---

## 8. Same Workflow, Different Global Variables (Parallel Execution)

**Purpose**: Verify different environment configs can run in parallel.

**Test**:
```bash
cat > /tmp/deploy.txt << 'EOF'
--instance-check

# Global variables
ENV=$ENVIRONMENT
TARGET=server-${ENV}

task=0
hostname=@TARGET@
exec=local
command=echo
arguments=Deploying to @ENV@
EOF

# Start prod and dev deployments
ENVIRONMENT=prod tasker -r /tmp/deploy.txt &
PID1=$!
ENVIRONMENT=dev tasker -r /tmp/deploy.txt &
PID2=$!

# Both should succeed
wait $PID1
EXIT1=$?
wait $PID2
EXIT2=$?

echo "Prod exit: $EXIT1 (should be 0)"
echo "Dev exit: $EXIT2 (should be 0)"
```

**Expected**:
- Both workflows run successfully
- Two different lock files (different global var values = different hash)
- Demonstrates the power of hash-based locking

---

## 9. SIGKILL (Kill -9) Cleanup

**Purpose**: Verify stale lock detection after hard kill.

**Test**:
```bash
# Start long-running workflow
tasker -r /tmp/long_task.txt --instance-check &
PID=$!

# Wait a moment for lock to be acquired
sleep 1

# Hard kill (no cleanup possible)
kill -9 $PID

# Verify lock file still exists
ls -la ~/TASKER/locks/

# Try to run again - should detect stale lock and succeed
tasker -r /tmp/long_task.txt --instance-check --debug 2>&1 | grep -i "stale\|lock"
```

**Expected**:
- First run creates lock
- Kill -9 leaves lock file behind
- Second run detects PID not running
- Logs: "# Stale lock detected (PID xxx not running), removing..."
- Successfully acquires lock and runs

**Current Implementation**: ✅ Implemented via `_is_process_running()` check

---

## 10. Network Filesystem (NFS/CIFS)

**Purpose**: Verify fcntl locks work on network filesystems.

**Setup**:
```bash
# Mount NFS share
sudo mount -t nfs server:/export ~/TASKER

# Or CIFS
sudo mount -t cifs //server/share ~/TASKER
```

**Test**:
```bash
# Run workflow with instance check
tasker -r task.txt --instance-check
```

**Expected Behavior**:
- NFS: fcntl locks may not work reliably
- CIFS: fcntl locks may not be supported
- **Warning**: Instance control may not work on network filesystems

**Current Status**: ⚠️ No special handling - users should use local filesystem

**Recommendation**: Add check for network filesystem and warn user.

---

## Summary

**Automated Tests** (in test_cases/functional/):
- ✅ test_instance_control_different_env.txt
- ✅ test_instance_control_force_instance.txt (blocked in files)
- ✅ test_instance_control_validate_only_bypass.txt
- 🔄 test_instance_control_corrupted_lock.txt (to be added)

**Manual Tests** (documented above):
- Race condition (multi-process)
- PID reuse (kernel-dependent)
- Symlink attack (requires setup)
- Disk full (system-level)
- Missing directory (basic case automated)
- Multiple workflows (multi-process)
- Different env vars (multi-process)
- SIGKILL cleanup (multi-process)
- Network filesystem (infrastructure-dependent)

**Testing Recommendation**:
Run manual tests before:
- Major releases
- After changes to instance control code
- When deploying to new environments (especially NFS/CIFS)
