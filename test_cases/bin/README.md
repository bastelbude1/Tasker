# Supporting Scripts for TASKER Test Cases

This directory contains utility and mock execution scripts used BY test cases during execution.

## 📋 Mock Execution Scripts

### **pbrun** (Production Business Run)
- **Purpose**: Mock execution environment for business logic tests
- **Usage**: Called by test cases that specify `exec=pbrun`
- **Source**: Moved from `../test_scripts/pbrun`

### **p7s** (Platform 7 System)
- **Purpose**: Mock execution environment for platform-specific tests
- **Usage**: Called by test cases that specify `exec=p7s`
- **Source**: Moved from `../test_scripts/p7s`

### **wwrs_clir** (Web Workflow Response System CLI)
- **Purpose**: Mock execution environment for CLI interface tests
- **Usage**: Called by test cases that specify `exec=wwrs_clir`
- **Source**: Moved from `../test_scripts/wwrs_clir`

## 🔧 Test Utility Scripts

### **increment_counter.sh**
- **Purpose**: Increments a counter file for testing sequential operations
- **Usage**: Called by test cases that need to track execution counts
- **Example**: Used in parallel execution tests to verify task completion

### **toggle_exit.sh**
- **Purpose**: Toggles exit status for testing conditional logic
- **Usage**: Called by test cases that need alternating success/failure states
- **Example**: Used in retry logic tests and conditional execution tests

## 🚀 Usage Notes

### **PATH Setup**
All test execution scripts should include:
```bash
export PATH="../bin:$PATH"
```

This ensures test cases can find these supporting scripts during execution.

### **Script Dependencies**
- These scripts are dependencies for test cases, not standalone executables
- Test cases reference these scripts via the `exec=` parameter
- Scripts maintain mock execution environments for testing

### **Script Permissions**
All scripts maintain executable permissions (`chmod +x`) for proper test execution.

---

*Supporting scripts for TASKER Test Suite*
*Organized for clear separation of test utilities vs execution scripts*