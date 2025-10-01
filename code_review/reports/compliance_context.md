# TASKER Compliance Review Context

## Python 3.6.8 Compatibility Requirements
TASKER must maintain strict Python 3.6.8 compatibility with NO external dependencies.

## FORBIDDEN Python 3.7+ Features
❌ **subprocess.run(capture_output=True, text=True)** - capture_output added in 3.7
❌ **subprocess.run(text=True)** - text parameter added in 3.7
❌ **f-string = specifier: f"{var=}"** - added in 3.8
❌ **dict.values() with walrus operator :=** - added in 3.8
❌ **Any external dependencies** - standard library only

## REQUIRED Python 3.6.8 Patterns
✅ **subprocess.Popen()** with universal_newlines=True for text mode
✅ **process.communicate(timeout=X)** for output capture with timeout
✅ **Manual process.returncode** checking instead of subprocess.run().returncode
✅ **with subprocess.Popen(...) as process:** for proper resource management

## CLAUDE.md Compliance Requirements
1. **Backup Policy**: All changes must have backup procedures
2. **1:1 Code Copy**: Minimize changes during refactoring
3. **Verification Testing**: 100% test success rate required
4. **ASCII-safe characters**: No Unicode characters in source code
5. **Error handling standards**: Consistent error patterns
6. **No inline comments**: Clean code in test cases
7. **Documentation synchronization**: Keep docs updated with code

## Coding Standards
- **Standard library only**: No pip dependencies allowed
- **Error handling**: Comprehensive exception handling patterns
- **Logging consistency**: Use callback-based logging throughout
- **Resource cleanup**: Proper file/process cleanup
- **Type safety**: Use appropriate type hints where possible (3.6.8 compatible)
- **Documentation**: Clear docstrings and comments
- **Testing**: Complete test coverage for all functionality

## Security Compliance
- **Input validation**: All user input must be validated
- **Command execution**: Safe subprocess patterns only
- **File operations**: Path validation and safe file handling
- **Error messages**: No sensitive information leakage

## Performance Compliance
- **Memory efficiency**: Handle large outputs appropriately
- **Resource limits**: Proper timeout and cancellation
- **Threading safety**: Safe concurrent operations
- **Algorithm efficiency**: Optimal data structures and algorithms
