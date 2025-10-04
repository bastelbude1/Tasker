# Legacy Test Scripts

This directory contains deprecated, redundant, or specialized legacy scripts that are preserved for historical reference but are not part of the active testing workflow.

## 📋 Legacy Scripts

### **compare_refactored.sh**
- **Purpose**: Legacy comparison between original and refactored code
- **Status**: ❌ Deprecated - refactoring complete
- **Replacement**: Use `focused_verification.sh` for current testing

### **comprehensive_comparison.sh**
- **Purpose**: Legacy comprehensive comparison logic
- **Status**: ❌ Deprecated - functionality integrated into other scripts
- **Replacement**: Use `comprehensive_verification.sh`

### **extended_verification_test.sh**
- **Purpose**: Extended verification testing (legacy)
- **Status**: ❌ Redundant with current verification scripts
- **Replacement**: Use `complete_system_validation.sh`

### **quick_test.sh**
- **Purpose**: Minimal quick test of core files
- **Status**: ❌ Redundant with `quick_verification_test.sh`
- **Replacement**: Use `scripts/quick_verification_test.sh`

### **quick_test_improved.sh**
- **Purpose**: Improved version of quick test
- **Status**: ❌ Redundant with current quick verification
- **Replacement**: Use `scripts/quick_verification_test.sh`

### **safe_parallel_test.sh**
- **Purpose**: Parallel testing safety validation
- **Status**: ⚠️ Specialized - may be needed for debugging parallel issues
- **Notes**: Keep for specialized parallel testing scenarios

### **test_failure_detection.sh**
- **Purpose**: Test failure detection mechanisms
- **Status**: ⚠️ Specialized - may be needed for debugging test failures
- **Notes**: Keep for debugging test execution issues

### **test_nested_parallel.sh**
- **Purpose**: Nested parallel execution testing
- **Status**: ⚠️ Specialized - may be needed for debugging nested parallel issues
- **Notes**: Keep for specialized nested parallel testing

## ⚠️ Usage Warning

**These scripts are NOT part of the active testing workflow:**
- They may use outdated paths and directory structures
- They may have compatibility issues with current TASKER version
- They are preserved for historical reference only

**Before using any legacy script:**
1. Review the script for compatibility issues
2. Update paths to work with new directory structure
3. Consider if current scripts provide the same functionality

## 🔄 Migration Notes

Scripts in this directory were moved during the test suite reorganization:
- **Date**: October 2025
- **Reason**: Redundancy, deprecation, or specialized use cases
- **Active Replacements**: Available in `scripts/` directory

---

*Legacy scripts preserved for historical reference*
*Not part of active TASKER testing workflow*