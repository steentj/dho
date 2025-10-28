# Failure Tracking Bugs - Analysis & Fixes

**Creation date/time**: 7. oktober 2025, 14:45  
**Last Modified date/time**: 7. oktober 2025, 14:45

## Executive Summary

Three critical bugs cause book processing failures to be incorrectly tracked and reported:

1. **OpenAI error details are lost** - error messages show as empty strings
2. **Wrapper reports wrong counts** - assumes all books succeeded regardless of actual failures
3. **Failed books not saved** - `failed_books.json` is never created when books fail

These bugs prevent automatic retry of failed books and make debugging impossible.

## Production Evidence

From log file `opret_bøger_2025-10-07_12-13-27.log`:

```
2025-10-07 12:16:14,233 - ERROR - Fejl ved behandling af http://dis-danmark.dk/bibliotek/900057.pdf: RuntimeError
RuntimeError: OpenAI embedding failed after 2 attempt(s):    <-- EMPTY ERROR MESSAGE

2025-10-07 12:19:51,556 - INFO - Processing completed: 6 successful, 4 failed out of 10 total  <-- ORCHESTRATOR
2025-10-07 12:19:51,566 - INFO - Behandling afsluttet: 10 vellykket, 0 fejlet  <-- WRAPPER (WRONG!)
```

**Expected result**: `book_failed/failed_books.json` with 4 failed URLs  
**Actual result**: File not created, retry functionality broken

---

## Bug #1: Empty Error Messages

### Location
`create_embeddings/providers/embedding_providers.py`, lines 120-139

### Code
```python
async def get_embedding(self, chunk: str):
    # ... retry logic ...
    while attempt <= max_retries:
        try:
            return await asyncio.wait_for(self._call_openai(chunk), timeout=timeout)
        except Exception as e:
            last_error = e
            # ...
    raise RuntimeError(f"OpenAI embedding failed after {attempt+1} attempt(s): {last_error}")
```

### Problem
When `last_error` is converted to string in the f-string, the actual exception details are lost or become empty. This makes debugging impossible.

### Root Cause
Generic `Exception` handling combined with insufficient error detail extraction.

### Fix Required
```python
raise RuntimeError(
    f"OpenAI embedding failed after {attempt+1} attempt(s): "
    f"{type(last_error).__name__}: {str(last_error)}"
)
```

### Test
`test_failure_tracking_bug.py::TestOpenAIErrorMessageBug::test_openai_error_message_is_preserved`

This test will **FAIL** until the error message preservation is fixed.

---

## Bug #2: Incorrect Success/Failure Counts

### Location
`create_embeddings/book_processor_wrapper.py`, lines 113-118

### Code
```python
# Update counters based on orchestrator results
# Note: For now, we assume success since orchestrator doesn't return detailed counts
# This could be enhanced to track individual results
self.processed_count = self.total_count
self.failed_count = 0
```

### Problem
The wrapper **blindly assumes all books succeeded**, regardless of actual orchestrator results. The comment even acknowledges this is wrong but says "This could be enhanced" - it's not optional, it's a critical bug.

### Data Flow Issue
```
Orchestrator (has real counts) -> Returns None -> Wrapper (assumes success)
                                                           ↓
                                           Logs wrong counts: "10 vellykket, 0 fejlet"
```

### Root Cause
`BookProcessingOrchestrator.process_books_from_urls()` returns `None` instead of results.

### Fix Required

**Step 1**: Modify orchestrator to return results:
```python
# In book_processing_orchestrator.py
async def process_books_from_urls(self, book_urls: List[str]) -> dict:
    # ... existing code ...
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successful = sum(1 for result in results if not isinstance(result, Exception))
    failed = len(results) - successful
    
    # Build detailed failure list
    failed_books = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            failed_books.append({
                'url': book_urls[i],
                'error': f"{type(result).__name__}: {str(result)}",
                'timestamp': datetime.now().isoformat()
            })
    
    return {
        'successful': successful,
        'failed': failed,
        'total': len(book_urls),
        'failed_books': failed_books
    }
```

**Step 2**: Modify wrapper to use returned results:
```python
# In book_processor_wrapper.py
results = await BookProcessingApplication.run_book_processing(...)

# Update counters from actual results
self.processed_count = results['successful']
self.failed_count = results['failed']
self.failed_books = results['failed_books']
```

### Tests
- `test_failure_tracking_bug.py::TestOrchestratorFailureReporting::test_orchestrator_returns_failure_details`
- `test_failure_tracking_bug.py::TestWrapperFailureTracking::test_wrapper_tracks_failures_from_orchestrator`

Both tests will **FAIL** until the orchestrator returns structured results.

---

## Bug #3: Failed Books Not Saved

### Location
`create_embeddings/book_processor_wrapper.py`, lines 54-57 and 123

### Code
```python
def save_failed_books(self):
    """Save failed books for retry"""
    if self.failed_books:  # <-- This list is ALWAYS EMPTY
        failed_file = self.failed_dir / "failed_books.json"
        with open(failed_file, 'w') as f:
            json.dump(self.failed_books, f, indent=2)

# Later in process_books_from_file():
self.save_failed_books()  # <-- Called but does nothing because list is empty
```

### Problem
`self.failed_books` is initialized as empty list and **never populated** because:
1. Orchestrator tracks failures internally but doesn't return them
2. Wrapper assumes all succeeded (Bug #2)
3. Therefore `self.failed_books` remains `[]`

### Consequence
- `failed_books.json` is never created
- `process_books.sh --retry-failed` has nothing to retry
- Manual intervention required to identify and reprocess failed books

### Fix Required
Fixed automatically by Bug #2 fix - once wrapper receives failure details from orchestrator, it can populate `self.failed_books`.

### Test
`test_failure_tracking_bug.py::TestWrapperFailureTracking::test_failed_books_saved_to_json`

This test will **FAIL** until wrapper tracks failures correctly.

---

## Architecture Flaw: Missing Return Values

The core issue is architectural:

```
Current (broken):
┌─────────────────┐
│  Orchestrator   │ Tracks failures internally
│  (has counts)   │ Logs: "6 successful, 4 failed"
└────────┬────────┘
         │ Returns: None
         ↓
┌────────────────┐
│    Wrapper     │ No failure info received
│  (assumes OK)  │ Logs: "10 vellykket, 0 fejlet"
└────────────────┘
```

```
Fixed (correct):
┌─────────────────┐
│  Orchestrator   │ Tracks failures internally
│  (has counts)   │ Logs: "6 successful, 4 failed"
└────────┬────────┘
         │ Returns: {successful: 6, failed: 4, failed_books: [...]}
         ↓
┌────────────────┐
│    Wrapper     │ Uses returned data
│  (tracks real  │ Logs: "6 vellykket, 4 fejlet"
│   results)     │ Saves: failed_books.json
└────────────────┘
```

---

## Implementation Plan

### Phase 1: Error Message Preservation
- [ ] Fix OpenAI error message formatting in `embedding_providers.py`
- [ ] Run test: `test_openai_error_message_is_preserved`
- [ ] Verify test passes

### Phase 2: Return Values from Orchestrator
- [ ] Modify `BookProcessingOrchestrator.process_books_from_urls()` to return dict
- [ ] Modify `BookProcessingApplication.run_book_processing()` to pass through results
- [ ] Run test: `test_orchestrator_returns_failure_details`
- [ ] Verify test passes

### Phase 3: Wrapper Failure Tracking
- [ ] Modify wrapper to receive and use orchestrator results
- [ ] Update counters: `processed_count`, `failed_count`
- [ ] Populate `failed_books` list
- [ ] Run test: `test_wrapper_tracks_failures_from_orchestrator`
- [ ] Verify test passes

### Phase 4: Failed Books JSON
- [ ] Verify `save_failed_books()` creates file with populated list
- [ ] Run test: `test_failed_books_saved_to_json`
- [ ] Verify test passes

### Phase 5: Integration Testing
- [ ] Process test batch with known failures
- [ ] Verify `failed_books.json` created correctly
- [ ] Verify retry functionality works: `process_books.sh --retry-failed`

### Phase 6: Full Test Suite
- [ ] Run all tests: `python -m pytest`
- [ ] Ensure no regressions in other areas
- [ ] Update documentation

---

## Test Strategy

### Test File Location
`create_embeddings/tests/test_failure_tracking_bug.py`

### Test Coverage

1. **OpenAI Error Messages**
   - `test_openai_error_message_is_preserved` - verifies timeout errors preserved
   - `test_openai_error_with_api_error` - verifies API errors preserved

2. **Orchestrator Return Values**
   - `test_orchestrator_returns_failure_details` - verifies structured results

3. **Wrapper Failure Tracking**
   - `test_wrapper_tracks_failures_from_orchestrator` - verifies counters
   - `test_failed_books_saved_to_json` - verifies JSON file creation

4. **Log Consistency**
   - `test_log_messages_are_consistent` - verifies orchestrator/wrapper logs match

5. **Integration Scenario**
   - `test_production_failure_scenario` - simulates actual production bug

### Running Tests

```bash
# Run all failure tracking tests
python -m pytest create_embeddings/tests/test_failure_tracking_bug.py -v

# Run specific test
python -m pytest create_embeddings/tests/test_failure_tracking_bug.py::TestOpenAIErrorMessageBug::test_openai_error_message_is_preserved -v

# Run with coverage
python -m pytest create_embeddings/tests/test_failure_tracking_bug.py --cov=create_embeddings
```

### Expected Results Before Fix
All tests in `test_failure_tracking_bug.py` will **FAIL** - this is expected and correct. They document the bugs.

### Expected Results After Fix
All tests should **PASS**, indicating:
- Error messages are preserved
- Orchestrator returns results
- Wrapper tracks failures correctly
- Failed books are saved to JSON
- Retry functionality works

---

## Manual Verification Steps

After implementing fixes, verify with real PDFs:

1. **Create test input file** with known-bad URLs:
   ```bash
   cat > test_failures.txt << EOF
   http://example.com/good.pdf
   http://invalid-domain-12345.com/bad.pdf
   http://example.com/good2.pdf
   EOF
   ```

2. **Run processing**:
   ```bash
   ./scripts/process_books.sh --file test_failures.txt
   ```

3. **Verify error messages** in log:
   ```bash
   grep "OpenAI embedding failed" soegemaskine/book_output/opret_bøger_*.log
   # Should show: "OpenAI embedding failed after 2 attempt(s): TimeoutError: Request timed out"
   # NOT: "OpenAI embedding failed after 2 attempt(s): "
   ```

4. **Verify counts** in log:
   ```bash
   tail soegemaskine/book_output/opret_bøger_*.log
   # Should show consistent counts:
   # "Processing completed: 2 successful, 1 failed out of 3 total"
   # "Behandling afsluttet: 2 vellykket, 1 fejlet"
   ```

5. **Verify failed_books.json**:
   ```bash
   cat soegemaskine/book_failed/failed_books.json
   # Should contain 1 entry with URL, error, timestamp
   ```

6. **Test retry**:
   ```bash
   ./scripts/process_books.sh --retry-failed
   # Should attempt to reprocess the 1 failed book
   ```

---

## Impact Assessment

### Current Impact (Production)
- ❌ **4 books failed** in last run (40% failure rate)
- ❌ **No automatic retry** possible - failed_books.json not created
- ❌ **Cannot debug** - error messages are empty
- ❌ **Manual intervention required** - must identify failed URLs from logs
- ❌ **Data loss risk** - books silently missing from database

### After Fix
- ✅ **Clear error messages** enable debugging
- ✅ **Accurate reporting** shows real success/failure counts
- ✅ **Automatic retry** via `process_books.sh --retry-failed`
- ✅ **Audit trail** in `failed_books.json`
- ✅ **Complete dataset** - no silently missing books

---

## Cross-Area Impact Check

Per development principles, verify no side effects in:

### 1. Book Processing Functionality
- ✅ All existing book processing tests must pass
- ✅ Verify `test_book_processing_orchestrator.py`
- ✅ Verify `test_book_processing_pipeline.py`

### 2. Search Functionality
- ✅ No changes to search code
- ✅ No impact expected
- ✅ Run search tests to confirm: `python -m pytest soegemaskine/tests/`

### 3. API Test GUI Functionality
- ✅ No changes to GUI code
- ✅ No impact expected

### 4. Shared Providers
- ✅ Embedding provider error handling changed
- ✅ Verify all provider tests pass
- ✅ Verify `test_providers.py`

---

## References

- **Log file**: `soegemaskine/book_output/opret_bøger_2025-10-07_12-13-27.log`
- **Test file**: `create_embeddings/tests/test_failure_tracking_bug.py`
- **Architecture doc**: `documentation/CORE/01_ARKITEKTUR.md`
- **Development principles**: `.github/copilot-instructions.md`

---

## Checklist for AI Agent

When fixing these bugs, ensure:

- [ ] Plan fixes in tiny, testable steps
- [ ] Write/update tests for each step
- [ ] Run tests after each change
- [ ] Wait for manual confirmation before proceeding
- [ ] Verify all tests in ALL areas pass
- [ ] Check for cross-area impacts
- [ ] Update documentation
- [ ] Create/update markdown plans with to-do's
