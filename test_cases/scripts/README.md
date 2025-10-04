# General Test Execution Scripts

This directory contains general test execution scripts that work across multiple test categories or provide specialized testing functionality.

## 🧪 NEW: Metadata-Driven Testing

**IMPORTANT**: TASKER now uses metadata-driven testing for all new and modified test cases.

### **Key Benefits**
- **Beyond Exit Codes**: Validates execution paths, variables, timing, resource usage
- **Self-Documenting**: Each test clearly states its purpose and expectations
- **Security Testing**: Proper validation of security test scenarios
- **Performance Monitoring**: Built-in performance benchmarking capabilities
- **Future-Proof**: Extensible metadata system for new validation types

### **Requirements for New Tests**
All new test cases MUST include TEST_METADATA:
```bash
# TEST_METADATA: {"description": "Test purpose", "test_type": "positive", "expected_exit_code": 0, "expected_success": true}
```

### **Migration Strategy**
- **Phase 1**: All functional tests and new test cases
- **Phase 2**: Integration and edge case tests
- **Phase 3**: Specialized and security tests

### **Resources**
- **Templates**: See `../templates/` for ready-to-use templates
- **Specification**: See `../TEST_METADATA_SPECIFICATION.md` for complete documentation
- **Examples**: See `../functional/metadata_*.txt` for working examples
- **Guidelines**: See `../../CLAUDE.md` for Claude Code enforcement policies

## 🎯 Primary Testing Scripts

### **intelligent_test_runner.py** ⭐ **NEW STANDARD**
- **Purpose**: Metadata-driven test execution with sophisticated validation
- **Usage**: `./intelligent_test_runner.py test_file.txt` or `./intelligent_test_runner.py directory/`
- **Coverage**: Execution path, variable validation, performance benchmarking, security testing
- **Features**: Beyond exit codes - validates expected behavior, timing, resource usage
- **Time**: Variable based on test complexity
- **Status**: ✅ Ready for production use

### **focused_verification.sh** ⭐ **LEGACY STANDARD**
- **Purpose**: Traditional exit code testing for daily development and validation
- **Usage**: `./focused_verification.sh`
- **Coverage**: All functional, edge_cases, and integration tests
- **Time**: ~5-10 minutes
- **Updated**: ✅ Works with new directory structure
- **Note**: ⚠️ Basic exit code validation only - consider migrating to intelligent_test_runner.py

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
- **Note**: ⚠️ Consider intelligent_test_runner.py for new tests with metadata

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