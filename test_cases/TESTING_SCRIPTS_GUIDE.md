# TASKER Testing Scripts Usage Guide

## 📋 Overview

This guide provides a clear overview of all testing scripts available in the TASKER test suite, their purposes, and when to use each one.

## 🚀 Quick Reference - Which Script Should I Use?

| **Scenario** | **Recommended Script** | **Time** | **Coverage** |
|--------------|------------------------|----------|--------------|
| **Quick sanity check** | `./quick_verification_test.sh` | ~30s | Representative sample |
| **Daily development** | `./focused_verification.sh` | ~5-10min | All functional tests |
| **Pre-commit validation** | `./focused_verification.sh` | ~5-10min | All functional tests |
| **Full system validation** | `./complete_system_validation.sh` | ~15-30min | Everything + security |
| **Security testing only** | `./security/security_test_runner.sh` | ~2-5min | Security tests only |
| **Behavioral validation** | `./enhanced_test_validator.py` | ~2-5min | Deep behavior analysis |
| **Regression testing** | `./comprehensive_verification.sh` | ~10-20min | Comprehensive behavior |

---

## 📚 Detailed Script Documentation

### 🎯 **Primary Testing Scripts** (Use These)

#### 1. `./focused_verification.sh` ⭐ **RECOMMENDED**
**Purpose**: Main testing script for daily development and validation

**What it does**:
- Tests all functional, edge_cases, and integration tests
- Updated for new directory structure
- Includes security validation testing (negative tests)
- Requires 100% success rate
- 60-second timeout per test

**When to use**:
- ✅ Daily development verification
- ✅ Pre-commit validation
- ✅ CI/CD pipeline testing
- ✅ After making code changes

**Usage**:
```bash
./focused_verification.sh
```

**Expected output**: 100% success rate for functional tests, security tests should fail

---

#### 2. `./complete_system_validation.sh` ⭐ **COMPREHENSIVE**
**Purpose**: Full system validation with enhanced behavioral testing

**What it does**:
- Tests standard functionality with comprehensive validation
- Tests security functionality (negative testing)
- Enhanced behavior validation beyond exit codes
- False positive detection
- Performance validation

**When to use**:
- ✅ Release validation
- ✅ Major feature testing
- ✅ Full regression testing
- ✅ Quality assurance validation

**Usage**:
```bash
./complete_system_validation.sh
```

**Expected output**: Detailed validation reports with comprehensive metrics

---

#### 3. `./enhanced_test_validator.py` ⭐ **BEHAVIORAL**
**Purpose**: Deep behavioral validation beyond simple exit codes

**What it does**:
- Variable resolution validation
- Execution path validation
- Log content analysis
- Pattern-based regression detection
- Catches issues that exit code checking misses

**When to use**:
- ✅ Behavioral regression testing
- ✅ Complex workflow validation
- ✅ Debugging test failures
- ✅ Quality assurance deep-dive

**Usage**:
```bash
./enhanced_test_validator.py
```

**Expected output**: Comprehensive validation with detailed issue reports

---

#### 4. `./security/security_test_runner.sh` ⭐ **SECURITY**
**Purpose**: Dedicated security testing (negative testing)

**What it does**:
- Executes all security tests
- Validates they fail as expected (security tests MUST fail)
- Tests command injection, buffer overflow, malformed input
- Security vulnerability detection

**When to use**:
- ✅ Security-focused testing
- ✅ Penetration testing validation
- ✅ Security regression testing
- ✅ Compliance validation

**Usage**:
```bash
./security/security_test_runner.sh
```

**Expected output**: All security tests should FAIL (success = vulnerability)

---

### 🔧 **Quick Testing Scripts**

#### 5. `./quick_verification_test.sh`
**Purpose**: Fast sanity check with representative test sample

**What it does**:
- Tests basic functionality sample
- Quick parallel execution test
- Basic retry logic test
- Fast validation (~30 seconds)

**When to use**:
- ✅ Quick sanity checks
- ✅ Fast development iteration
- ✅ Initial validation

**Usage**:
```bash
./quick_verification_test.sh
```

---

#### 6. `./quick_test.sh`
**Purpose**: Minimal quick test of core files

**What it does**:
- Tests 3-4 core test files
- Very fast execution
- Basic functionality only

**When to use**:
- ✅ Ultra-fast sanity check
- ✅ Development iteration

**Usage**:
```bash
./quick_test.sh
```

---

### 📊 **Advanced/Specialized Scripts**

#### 7. `./comprehensive_verification.sh`
**Purpose**: Deep behavior validation with comparison analysis

**What it does**:
- Variable resolution correctness
- Execution path validation
- Log content analysis
- Pattern-based regression detection

**When to use**:
- ✅ Deep regression analysis
- ✅ Behavioral validation
- ✅ Complex issue debugging

---

#### 8. `./verify_all_tests.sh`
**Purpose**: Complete verification testing protocol

**What it does**:
- Tests ALL .txt files
- Functional behavior validation
- May include legacy comparison logic

**When to use**:
- ✅ Complete system verification
- ✅ Legacy compatibility testing

---

### 🔧 **Utility/Specialized Scripts**

#### 9. `./host_validation_test_runner.sh`
**Purpose**: Host validation specific testing

**What it does**:
- Tests host connectivity validation
- Host validation scenarios
- Network-related testing

**When to use**:
- ✅ Host validation testing
- ✅ Network connectivity testing

---

#### 10. `./retry_validation_test_script.sh`
**Purpose**: Retry logic specific validation

**What it does**:
- Focused retry logic testing
- Retry scenario validation

**When to use**:
- ✅ Retry logic testing
- ✅ Failure recovery validation

---

#### 11. `./unit_test_non_blocking_sleep.py`
**Purpose**: Unit testing for non-blocking sleep functionality

**What it does**:
- Python unit tests
- Non-blocking sleep testing
- Isolated component testing

**When to use**:
- ✅ Unit testing
- ✅ Component isolation testing

---

### ⚠️ **Legacy/Specialized Scripts** (Consider Before Using)

- `./extended_verification_test.sh` - Extended verification (may be redundant)
- `./quick_test_improved.sh` - Improved quick test (check if still needed)
- `./safe_parallel_test.sh` - Parallel testing safety
- `./test_failure_detection.sh` - Test failure detection
- `./test_nested_parallel.sh` - Nested parallel testing

---

## 🏗️ **Script Compatibility with New Organization**

| Script | **Updated for New Structure** | **Status** | **Notes** |
|--------|-------------------------------|------------|-----------|
| `focused_verification.sh` | ✅ **YES** | **READY** | Updated to use new directory structure |
| `complete_system_validation.sh` | ⚠️ **NEEDS UPDATE** | **REVIEW NEEDED** | May need path updates |
| `enhanced_test_validator.py` | ⚠️ **NEEDS UPDATE** | **REVIEW NEEDED** | May need path updates |
| `security_test_runner.sh` | ✅ **YES** | **READY** | Already in security/ directory |
| `quick_verification_test.sh` | ❌ **NO** | **NEEDS UPDATE** | Uses old file paths |
| Others | ❌ **NO** | **NEEDS UPDATE** | Most use old structure |

---

## 📋 **Recommended Testing Workflow**

### **Daily Development**:
1. `./quick_verification_test.sh` - Fast sanity check (30s)
2. `./focused_verification.sh` - Full functional validation (5-10min)

### **Pre-Commit**:
1. `./focused_verification.sh` - Ensure no regressions (5-10min)
2. `./security/security_test_runner.sh` - Security validation (2-5min)

### **Release Validation**:
1. `./complete_system_validation.sh` - Full system test (15-30min)
2. `./enhanced_test_validator.py` - Behavioral validation (2-5min)
3. `./comprehensive_verification.sh` - Deep analysis (10-20min)

### **Security Testing**:
1. `./security/security_test_runner.sh` - Security tests only (2-5min)

### **Debugging Issues**:
1. `./enhanced_test_validator.py` - Behavioral analysis
2. `./comprehensive_verification.sh` - Deep validation

---

## 🔧 **Script Update Status & TODO**

### **Priority Updates Needed**:

1. **`quick_verification_test.sh`** - Update for new directory structure
2. **`complete_system_validation.sh`** - Verify compatibility with new structure
3. **`enhanced_test_validator.py`** - Update test file paths
4. **`comprehensive_verification.sh`** - Update for new organization

### **Scripts to Consider Consolidating**:
- `quick_test.sh` vs `quick_verification_test.sh` - Similar purpose
- Multiple legacy verification scripts - May have overlapping functionality

---

## 💡 **Tips and Best Practices**

### **For Development**:
- Use `focused_verification.sh` as your primary testing script
- Run `quick_verification_test.sh` for fast iteration
- Always run security tests before major releases

### **For CI/CD**:
- Use `focused_verification.sh` for automated testing
- Include `security_test_runner.sh` for security validation
- Use `complete_system_validation.sh` for release validation

### **For Debugging**:
- Start with `enhanced_test_validator.py` for behavioral analysis
- Use individual test execution for specific issues:
  ```bash
  ../tasker.py functional/simple_test.txt -r --skip-host-validation --log-level=DEBUG
  ```

### **Exit Codes to Expect**:
- **0**: Success (functional tests)
- **5**: Success with `next=never`
- **20-21**: Validation failure (security tests - this is good!)
- **124**: Timeout (always a failure)

---

*Last updated: October 2025*
*TASKER Version: 2.0*
*Test Framework Version: 1.0*