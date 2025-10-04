# General Test Execution Scripts

This directory contains general test execution scripts that work across multiple test categories or provide specialized testing functionality.

## 🎯 Primary Testing Scripts

### **focused_verification.sh** ⭐ **RECOMMENDED**
- **Purpose**: Main testing script for daily development and validation
- **Usage**: `./focused_verification.sh`
- **Coverage**: All functional, edge_cases, and integration tests
- **Time**: ~5-10 minutes
- **Updated**: ✅ Works with new directory structure

### **complete_system_validation.sh** ⭐ **COMPREHENSIVE**
- **Purpose**: Full system validation with enhanced behavioral testing
- **Usage**: `./complete_system_validation.sh`
- **Coverage**: Standard + security + behavioral validation
- **Time**: ~15-30 minutes
- **Status**: ⚠️ May need path updates for new structure

### **enhanced_test_validator.py** ⭐ **BEHAVIORAL**
- **Purpose**: Deep behavioral validation beyond simple exit codes
- **Usage**: `./enhanced_test_validator.py`
- **Coverage**: Variable resolution, execution path, pattern validation
- **Time**: ~2-5 minutes
- **Updated**: ✅ Works with new directory structure

## 🔧 Quick Testing Scripts

### **quick_verification_test.sh**
- **Purpose**: Fast sanity check with representative test sample
- **Usage**: `./quick_verification_test.sh`
- **Coverage**: Representative sample from all categories
- **Time**: ~30 seconds
- **Updated**: ✅ Works with new directory structure

### **verify_all_tests.sh**
- **Purpose**: Complete verification testing protocol
- **Usage**: `./verify_all_tests.sh`
- **Coverage**: ALL .txt files with functional behavior validation
- **Time**: Variable

## 📊 Advanced/Specialized Scripts

### **comprehensive_verification.sh**
- **Purpose**: Deep behavior validation with comparison analysis
- **Usage**: `./comprehensive_verification.sh`
- **Coverage**: Variable resolution, execution path, log analysis
- **Time**: ~10-20 minutes

### **host_validation_test_runner.sh**
- **Purpose**: Host validation specific testing
- **Usage**: `./host_validation_test_runner.sh`
- **Coverage**: Host connectivity validation scenarios

### **retry_validation_test_script.sh**
- **Purpose**: Retry logic specific validation
- **Usage**: `./retry_validation_test_script.sh`
- **Coverage**: Retry scenario validation

### **unit_test_non_blocking_sleep.py**
- **Purpose**: Unit testing for non-blocking sleep functionality
- **Usage**: `python3 unit_test_non_blocking_sleep.py`
- **Coverage**: Isolated component testing

## 📋 Usage Guidelines

### **PATH Setup**
All scripts should include:
```bash
export PATH="../bin:$PATH"
```

### **Log Output**
All scripts that write logs should use:
```bash
LOG_DIR="../logs"
```

### **Recommended Workflow**
1. **Daily Development**: `./focused_verification.sh`
2. **Pre-Commit**: `./focused_verification.sh`
3. **Release Validation**: `./complete_system_validation.sh`
4. **Debugging**: `./enhanced_test_validator.py`

---

*General test execution scripts for TASKER Test Suite*
*Scripts that work across multiple test categories*