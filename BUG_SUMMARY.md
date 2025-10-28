# Bug Analysis Summary - Book Processing Failures

**Date**: 7. oktober 2025

## What Happened

You processed 10 books, but the system reported **contradictory results**:
- Orchestrator correctly logged: "6 successful, 4 failed"  
- Wrapper incorrectly logged: "10 vellykket, 0 fejlet"
- No `failed_books.json` created for retry

## Three Critical Bugs Found

### Bug #1: OpenAI Error Messages Are Empty
**Symptom**: `RuntimeError: OpenAI embedding failed after 2 attempt(s): ` (nothing after colon)

**Location**: `create_embeddings/providers/embedding_providers.py` line 139

**Problem**: Error details lost when converting exception to string

**Fix**: 
```python
raise RuntimeError(f"OpenAI embedding failed after {attempt+1} attempt(s): {type(last_error).__name__}: {str(last_error)}")
```

---

### Bug #2: Wrapper Reports Wrong Counts
**Symptom**: Logs "10 vellykket, 0 fejlet" when actually 6 succeeded, 4 failed

**Location**: `create_embeddings/book_processor_wrapper.py` lines 113-118

**Problem**: Code literally says:
```python
# Note: For now, we assume success since orchestrator doesn't return detailed counts
self.processed_count = self.total_count  # Assumes ALL succeeded!
self.failed_count = 0
```

**Fix**: Orchestrator must return results, wrapper must use them

---

### Bug #3: Failed Books Not Saved
**Symptom**: `soegemaskine/book_failed/failed_books.json` not created

**Location**: `create_embeddings/book_processor_wrapper.py` lines 54-57

**Problem**: `self.failed_books` list is always empty because wrapper assumes all succeeded (Bug #2)

**Fix**: Fixed automatically when Bug #2 is fixed

---

## Why This Is Critical

1. **Cannot debug** - empty error messages make it impossible to know what went wrong
2. **Cannot retry** - no `failed_books.json` means `--retry-failed` has nothing to retry  
3. **Data loss** - books silently missing from database with no audit trail
4. **Wrong metrics** - reports show 100% success when reality is 60% success

---

## Tests Created

I've created **comprehensive tests** in:
```
create_embeddings/tests/test_failure_tracking_bug.py
```

**These tests will FAIL** - that's correct and expected! They document the bugs.

### Test Classes:
1. `TestOpenAIErrorMessageBug` - proves error messages are empty
2. `TestOrchestratorFailureReporting` - proves orchestrator doesn't return results
3. `TestWrapperFailureTracking` - proves wrapper doesn't track failures  
4. `TestEndToEndFailureScenario` - simulates your exact production bug
5. `TestLogInconsistencyBug` - proves log messages contradict each other

---

## Next Steps (DO NOT IMPLEMENT YET)

Full details in `/documentation/TEKNISK/FAILURE_TRACKING_BUGS.md`

**The fixes require:**

1. Preserve error messages in OpenAI provider
2. Make orchestrator return structured results:
   ```python
   return {
       'successful': 6,
       'failed': 4,
       'failed_books': [
           {'url': '...', 'error': '...', 'timestamp': '...'},
           ...
       ]
   }
   ```
3. Make wrapper use those results instead of assuming success
4. Verify `failed_books.json` gets created correctly

---

## How to Verify Bugs Exist

Run the tests I created:

```bash
# Run all bug tests (will FAIL - that's expected)
python -m pytest create_embeddings/tests/test_failure_tracking_bug.py -v

# Run specific test
python -m pytest create_embeddings/tests/test_failure_tracking_bug.py::TestOpenAIErrorMessageBug -v
```

---

## Documents Created

1. **Test file**: `create_embeddings/tests/test_failure_tracking_bug.py`
   - Comprehensive test coverage
   - Tests will fail until bugs are fixed
   - Documents expected vs actual behavior

2. **Technical analysis**: `documentation/TEKNISK/FAILURE_TRACKING_BUGS.md`
   - Complete bug analysis
   - Architecture diagrams
   - Implementation plan
   - Manual verification steps

---

## Your Current Failed Books

From your log, these 4 URLs failed:
1. http://dis-danmark.dk/bibliotek/900057.pdf
2. http://dis-danmark.dk/bibliotek/900015.pdf
3. http://dis-danmark.dk/bibliotek/900070.pdf
4. http://dis-danmark.dk/bibliotek/900060.pdf

**Manual workaround** until bugs are fixed:
```bash
cat > retry.txt << EOF
http://dis-danmark.dk/bibliotek/900057.pdf
http://dis-danmark.dk/bibliotek/900015.pdf
http://dis-danmark.dk/bibliotek/900070.pdf
http://dis-danmark.dk/bibliotek/900060.pdf
EOF

./scripts/process_books.sh --file retry.txt
```

But you still won't see the actual error messages due to Bug #1.
