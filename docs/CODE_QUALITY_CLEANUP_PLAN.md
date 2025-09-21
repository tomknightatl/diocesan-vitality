# Code Quality Cleanup Plan

This document outlines a systematic approach to fix all 200+ flake8 code quality issues in the Diocesan Vitality codebase.

## Issue Analysis

Based on flake8 output, we have **364 total issues** across these categories:

| Category | Count | Priority | Description |
|----------|-------|----------|-------------|
| **F401** | 121 | High | Unused imports - Easy automated fixes |
| **C901** | 68 | Medium | Complex functions - Requires refactoring |
| **F541** | 60 | High | f-strings without placeholders - Easy fixes |
| **E402** | 32 | Medium | Import order issues - Easy fixes |
| **F841** | 31 | High | Unused variables - Easy fixes |
| **E722** | 30 | High | Bare except clauses - Moderate fixes |
| **E302** | 13 | Low | Missing blank lines - Easy fixes |
| **F824** | 3 | Low | Unused globals - Easy fixes |
| **F821** | 3 | High | Undefined names - Critical fixes |
| **F811** | 2 | Medium | Function redefinitions - Moderate fixes |
| **F403** | 1 | Low | Star imports - Easy fix |

## Execution Strategy

### Phase 1: Critical & Easy Fixes (Priority 1)
**Target**: Fix 151 issues (42% of total)
**Time Estimate**: 2-3 hours

#### 1.1 Undefined Names (F821) - CRITICAL
- Fix 3 undefined `time` references
- Ensure all variables are properly imported/defined

#### 1.2 Unused Imports (F401)
- Remove 121 unused import statements
- Use automated tools where possible
- Preserve imports needed for type hints

#### 1.3 Unused Variables (F841)
- Remove or use 31 unused local variables
- Convert to underscore prefix if intentionally unused

#### 1.4 f-string Issues (F541)
- Fix 60 f-strings that don't need to be f-strings
- Convert to regular strings or add missing placeholders

### Phase 2: Moderate Fixes (Priority 2)
**Target**: Fix 67 issues (18% of total)
**Time Estimate**: 3-4 hours

#### 2.1 Bare Except Clauses (E722)
- Replace 30 bare `except:` with specific exceptions
- Add proper exception handling

#### 2.2 Import Order (E402)
- Fix 32 module-level import positioning
- Move imports to top of files

#### 2.3 Function Redefinitions (F811)
- Resolve 2 duplicate function definitions
- Rename or consolidate duplicate functions

### Phase 3: Refactoring (Priority 3)
**Target**: Fix 68 issues (19% of total)
**Time Estimate**: 4-6 hours

#### 3.1 Complex Functions (C901)
- Refactor 68 overly complex functions
- Break down into smaller, focused functions
- Extract common logic into helper methods

### Phase 4: Style & Cleanup (Priority 4)
**Target**: Fix 17 issues (5% of total)
**Time Estimate**: 1 hour

#### 4.1 Formatting Issues
- Add 13 missing blank lines (E302)
- Fix 3 unused global declarations (F824)
- Replace 1 star import (F403)

## Detailed Execution Plan

### Phase 1.1: Critical Fixes (30 minutes)

```bash
# 1. Fix undefined 'time' references
grep -rn "undefined name 'time'" --include="*.py" .
# Add proper time imports where needed

# 2. Verify all critical errors are resolved
flake8 . --select=F821 --count
```

### Phase 1.2: Unused Imports (60 minutes)

```bash
# 1. Use autoflake to remove unused imports
pip install autoflake
autoflake --remove-all-unused-imports --in-place --recursive .

# 2. Manual review for type hint imports
# Check files that might need imports for typing
grep -r "from typing import" --include="*.py" .

# 3. Verify removal
flake8 . --select=F401 --count
```

### Phase 1.3: Unused Variables (45 minutes)

```bash
# 1. Find all unused variables
flake8 . --select=F841 --show-source

# 2. For each file, either:
#    - Remove the variable assignment
#    - Use the variable appropriately
#    - Prefix with underscore if intentionally unused

# 3. Common patterns to fix:
#    - result = some_function()  # but result never used
#    - e = exception  # in except blocks
#    - data = response.json()  # but data never used
```

### Phase 1.4: f-string Issues (45 minutes)

```bash
# 1. Find f-strings without placeholders
flake8 . --select=F541 --show-source

# 2. For each occurrence:
#    - Remove f prefix if no placeholders needed
#    - Add missing placeholders if variables should be included

# Example fixes:
# f"Loading data..."  →  "Loading data..."
# f"Processing {item}"  →  Keep as-is (has placeholder)
```

### Phase 2.1: Exception Handling (90 minutes)

```bash
# 1. Find all bare except clauses
flake8 . --select=E722 --show-source

# 2. Replace with specific exceptions:
# except:  →  except Exception as e:
# Consider more specific exceptions where appropriate:
# - except (ValueError, TypeError):
# - except WebDriverException:
# - except requests.RequestException:
```

### Phase 2.2: Import Order (60 minutes)

```bash
# 1. Find import order issues
flake8 . --select=E402 --show-source

# 2. Move imports to top of file (after docstrings)
# 3. Use isort to fix automatically:
isort . --profile black --check-diff
isort . --profile black
```

### Phase 3.1: Complex Function Refactoring (4-6 hours)

This is the most involved phase. For each complex function:

1. **Analyze the function** - understand what it does
2. **Identify logical sections** - break into smaller parts
3. **Extract helper methods** - create focused functions
4. **Reduce nesting** - use early returns, guard clauses
5. **Split responsibilities** - ensure single responsibility principle

**Target Functions by Complexity:**
- `'main_async' is too complex (11)` - Break down main async logic
- `get_parishes_for_diocese` (39) - Split into smaller functions
- `get_all_parishes` (35) - Extract filtering/processing logic
- `scrape_parish_data` (34) - Split scraping steps
- Functions with complexity 11-22 - Apply standard refactoring patterns

**Refactoring Patterns:**
```python
# Before: Complex function
def complex_function(data):
    # 50+ lines of mixed logic

# After: Refactored
def complex_function(data):
    validated_data = _validate_input(data)
    processed_data = _process_data(validated_data)
    return _format_output(processed_data)

def _validate_input(data):
    # focused validation logic

def _process_data(data):
    # focused processing logic

def _format_output(data):
    # focused formatting logic
```

## Quality Gates

After each phase, run validation:

```bash
# Check specific error types are resolved
flake8 . --select=F821 --count  # Should be 0
flake8 . --select=F401 --count  # Should be 0 after Phase 1.2
flake8 . --select=F841 --count  # Should be 0 after Phase 1.3

# Full quality check
flake8 . --count --max-complexity=10 --max-line-length=127

# Run tests to ensure functionality preserved
pytest tests/ -v
```

## File-by-File Priority

### High Priority Files (Critical path + Most issues):
1. `async_extract_parishes.py` - 8 issues, core functionality
2. `backend/main.py` - 7 issues, API endpoints
3. `core/ai_content_analyzer.py` - 12 issues, AI processing
4. `core/enhanced_url_manager.py` - 10 issues, URL handling
5. `extract_schedule.py` - 7 issues, schedule extraction

### Medium Priority Files:
- All `core/` modules with 3-5 issues each
- Extractor modules
- Test files with issues

### Low Priority Files:
- Example scripts
- Single-issue files
- Documentation-related scripts

## Automation Tools

```bash
# Install cleanup tools
pip install autoflake autopep8 isort black

# Automated fixes (run in order)
autoflake --remove-all-unused-imports --remove-unused-variables --in-place --recursive .
autopep8 --in-place --aggressive --recursive .
isort . --profile black
black . --line-length=127

# Manual review after automation
flake8 . --count --max-complexity=10 --max-line-length=127
```

## Success Metrics

- **Phase 1 Complete**: ≤50 remaining issues (86% reduction)
- **Phase 2 Complete**: ≤20 remaining issues (95% reduction)
- **Phase 3 Complete**: ≤5 remaining issues (98% reduction)
- **Phase 4 Complete**: 0 flake8 issues (100% clean)
- **CI/CD Pipeline**: Passes all quality gates
- **Tests**: All existing tests still pass
- **Functionality**: No regressions in core features

## Rollback Plan

If issues arise during cleanup:
1. **Git stash/commit** after each phase
2. **Test functionality** after each major change
3. **Revert specific files** if problems found
4. **Incremental approach** - fix one file at a time if needed

## Timeline

- **Phase 1**: 3 hours (Critical fixes)
- **Phase 2**: 4 hours (Moderate fixes)
- **Phase 3**: 6 hours (Refactoring)
- **Phase 4**: 1 hour (Final cleanup)
- **Testing**: 1 hour (Validation)

**Total Estimated Time**: 15 hours over 2-3 work sessions

## Benefits

After completion:
- ✅ CI/CD pipeline passes all quality checks
- ✅ Environment strategy can be fully tested
- ✅ Codebase maintainability significantly improved
- ✅ Reduced technical debt
- ✅ Better developer experience
- ✅ Preparation for future code quality enforcement