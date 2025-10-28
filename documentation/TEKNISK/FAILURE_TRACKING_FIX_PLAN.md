# Failure Tracking Bug Fixes - Implementation Plan

**Creation date/time**: 7. oktober 2025, 15:00  
**Last Modified date/time**: 7. oktober 2025, 15:00

## Overview

Implementation plan for fixing the three critical failure tracking bugs identified in `FAILURE_TRACKING_BUGS.md`.

## Phase 1: Fix Error Message Preservation ✅ NEXT

### Goal
Preserve complete error details in OpenAI embedding failures

### Tasks
- [✅] Task 1.1: Update error message formatting in `embedding_providers.py`
- [ ] Task 1.2: Run test `test_openai_error_message_is_preserved`
- [ ] Task 1.3: Verify test passes
- [ ] Task 1.4: Run full provider tests
- [ ] Task 1.5: Manual confirmation

### Expected Outcome
Error messages show: `"RuntimeError: OpenAI embedding failed after 2 attempt(s): TimeoutError: Request timed out"`

---

## Phase 2: Return Results from Orchestrator

### Goal
Orchestrator returns structured results instead of None

### Tasks
- [ ] Task 2.1: Import datetime in orchestrator
- [ ] Task 2.2: Update `process_books_from_urls()` return type
- [ ] Task 2.3: Build failed_books list in orchestrator
- [ ] Task 2.4: Return structured dict
- [ ] Task 2.5: Update `BookProcessingApplication.run_book_processing()` to return results
- [ ] Task 2.6: Run test `test_orchestrator_returns_failure_details`
- [ ] Task 2.7: Verify test passes
- [ ] Task 2.8: Run all orchestrator tests
- [ ] Task 2.9: Manual confirmation

### Expected Outcome
Orchestrator returns:
```python
{
    'successful': 6,
    'failed': 4,
    'total': 10,
    'failed_books': [
        {'url': '...', 'error': '...', 'timestamp': '...'},
        ...
    ]
}
```

---

## Phase 3: Update Wrapper to Use Results

### Goal
Wrapper receives and uses orchestrator results instead of assuming success

### Tasks
- [ ] Task 3.1: Update wrapper to receive results from orchestrator
- [ ] Task 3.2: Update counters from actual results
- [ ] Task 3.3: Populate failed_books list
- [ ] Task 3.4: Run test `test_wrapper_tracks_failures_from_orchestrator`
- [ ] Task 3.5: Verify test passes
- [ ] Task 3.6: Run test `test_failed_books_saved_to_json`
- [ ] Task 3.7: Verify test passes
- [ ] Task 3.8: Run all wrapper tests
- [ ] Task 3.9: Manual confirmation

### Expected Outcome
Wrapper logs: `"Behandling afsluttet: 6 vellykket, 4 fejlet"` (matching orchestrator)

---

## Phase 4: Integration Testing

### Goal
Verify complete failure tracking flow works end-to-end

### Tasks
- [ ] Task 4.1: Run all bug tests
- [ ] Task 4.2: Verify all pass
- [ ] Task 4.3: Run complete test suite
- [ ] Task 4.4: Verify no regressions
- [ ] Task 4.5: Manual confirmation

### Expected Outcome
All tests in `test_failure_tracking_bug.py` pass

---

## Phase 5: Manual Verification

### Goal
Test with actual book processing

### Tasks
- [ ] Task 5.1: Create test file with known failures
- [ ] Task 5.2: Run process_books.sh
- [ ] Task 5.3: Verify error messages are complete
- [ ] Task 5.4: Verify counts are accurate
- [ ] Task 5.5: Verify failed_books.json created
- [ ] Task 5.6: Test retry functionality
- [ ] Task 5.7: Manual confirmation

### Expected Outcome
- Complete error messages in logs
- Accurate success/failure counts
- failed_books.json created with details
- Retry works correctly

---

## Phase 6: Documentation Update

### Goal
Update all relevant documentation

### Tasks
- [ ] Task 6.1: Mark bugs as fixed in FAILURE_TRACKING_BUGS.md
- [ ] Task 6.2: Update BUG_SUMMARY.md
- [ ] Task 6.3: Update this plan with completion status
- [ ] Task 6.4: Commit all changes

---

## Success Criteria

- ✅ All tests in `test_failure_tracking_bug.py` pass
- ✅ All existing tests still pass (no regressions)
- ✅ Error messages show complete details including exception type
- ✅ Orchestrator and wrapper log consistent counts
- ✅ failed_books.json created when books fail
- ✅ Retry functionality works correctly
- ✅ Documentation updated

---

## Rollback Plan

If any phase fails:
1. Revert changes: `git checkout <file>`
2. Review test failures
3. Re-analyze issue
4. Update plan
5. Retry with corrected approach
