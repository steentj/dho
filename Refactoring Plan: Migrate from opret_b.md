# Refactoring Plan: Migrate from opret_bøger.py to book_processor_wrapper.py

## Creation date/time: 22. juli 2025, 12:45
## Last Modified date/time: 22. juli 2025, 12:45

## Objective
To complete the transition from using opret_bøger.py to book_processor_wrapper.py as the main entry point for the application, removing code duplication and consolidating functionality into the pipeline pattern.

## Background Analysis
- opret_bøger.py contains legacy code that's being gradually refactored
- book_processor_wrapper.py is a more modern implementation that serves as the main entry point
- `BookProcessingPipeline` is the target architecture using the pipeline pattern
- We need to move any remaining utility functions from opret_bøger.py to appropriate classes

## Step-by-Step Refactoring Plan

### Phase 1: Move URL Loading to Pipeline
1. Add a `load_urls_from_file` method to `BookProcessingPipeline`
2. Create a test adapter in `test_utils.py` for backward compatibility
3. Update book_processor_wrapper.py to use the new pipeline method
4. Update all tests that use `indlæs_urls` to use the adapter
5. Verify all tests pass

### Phase 2: Make Pipeline Methods Public
1. Evaluate if any `_` prefixed methods in `BookProcessingPipeline` should be made public
2. Update method names and documentation as needed
3. Update any code that calls these methods
4. Verify all tests pass

### Phase 3: Update BookProcessingApplication
1. Verify `BookProcessingApplication` is complete and doesn't need functions from opret_bøger.py
2. Ensure proper error handling and logging
3. Update any remaining references to opret_bøger.py functions
4. Verify all tests pass

### Phase 4: Remove process_book from opret_bøger.py
1. Identify all calls to `process_book` in the codebase
2. Update them to use `BookProcessingPipeline.process_book_from_url` directly
3. Create an adapter in `test_utils.py` if needed for tests
4. Verify all tests pass

### Phase 5: Eliminate opret_bøger.py
1. Ensure all functionality has been migrated
2. Update any remaining imports from opret_bøger.py
3. Remove the file
4. Verify all tests pass

### Phase 6: Update Documentation
1. Update any documentation that references opret_bøger.py
2. Create/update markdown docs explaining the pipeline architecture
3. Update comments in code to reflect the new architecture

## Detailed Tasks

### Phase 1: Move URL Loading to Pipeline

#### 1.1. Add load_urls_from_file method to BookProcessingPipeline
```python
def load_urls_from_file(self, file_path: str) -> list:
    """
    Load book URLs from a file.
    
    Args:
        file_path: Path to the file containing URLs
        
    Returns:
        List of URLs to process
    """
    logger.info(f"Loading URLs from {file_path}")
    with open(file_path, "r") as file:
        urls = [line.strip() for line in file.readlines() if line.strip()]
    logger.info(f"Loaded {len(urls)} URLs to process")
    return urls
```

#### 1.2. Create test adapter in test_utils.py
```python
def indlæs_urls_adapter(file_path: str) -> list:
    """
    Adapter function that provides the same interface as the old indlæs_urls
    but delegates to BookProcessingPipeline.load_urls_from_file.
    
    Args:
        file_path: Path to the file containing URLs
        
    Returns:
        List of URLs to process
    """
    # Create a minimal pipeline instance just for URL loading
    pipeline = BookProcessingPipeline(
        book_service=MagicMock(),
        embedding_provider=MagicMock(),
        chunking_strategy=MagicMock()
    )
    
    # Call the pipeline's method
    return pipeline.load_urls_from_file(file_path)
```

#### 1.3. Update book_processor_wrapper.py
Find the line:
```python
book_urls = indlæs_urls(str(input_file_path))
```
Replace with:
```python
# Create pipeline for URL loading
from .book_processing_pipeline import BookProcessingPipeline
temp_pipeline = BookProcessingPipeline(
    book_service=None,  # Will be set up later
    embedding_provider=None,  # Will be set up later
    chunking_strategy=None  # Will be set up later
)
book_urls = temp_pipeline.load_urls_from_file(str(input_file_path))
```

#### 1.4. Update imports in book_processor_wrapper.py
Find:
```python
from create_embeddings.opret_bøger import (
    indlæs_urls,
)
```
Remove the `indlæs_urls` import

#### 1.5. Update tests to use adapter
For each test file that imports `indlæs_urls`:
```python
# Old
from create_embeddings.opret_bøger import indlæs_urls

# New
from create_embeddings.tests.test_utils import indlæs_urls_adapter as indlæs_urls
```

### Phase 2: Make Pipeline Methods Public

#### 2.1. Evaluate methods in BookProcessingPipeline
Methods to consider making public:
- `_extract_text_by_page`
- `_parse_pdf_to_book_data`
- `_fetch_pdf`
- `_save_book_data`

#### 2.2. Update method names
For each method that should be public, rename by removing the underscore prefix:
```python
# Example: From
def _extract_text_by_page(self, pdf: fitz.Document) -> Dict[int, str]:
    
# To
def extract_text_by_page(self, pdf: fitz.Document) -> Dict[int, str]:
```

#### 2.3. Update method calls within the class
Update all internal calls to these methods (for each renamed method)

#### 2.4. Update test adapters
Update adapter functions in `test_utils.py` to use the new method names

### Phase 3: Update BookProcessingApplication

#### 3.1. Review BookProcessingApplication.run_book_processing
Ensure it doesn't depend on functions from opret_bøger.py

#### 3.2. Update error handling and logging
Add proper error handling and logging if needed

### Phase 4: Remove process_book from opret_bøger.py

#### 4.1. Identify all calls to process_book
Use grep or code search to find all calls

#### 4.2. Update calls to use BookProcessingPipeline directly
Replace each call with direct usage of the pipeline

#### 4.3. Create adapter in test_utils.py if needed
```python
async def process_book_adapter(book_url, chunk_size, book_service, session, embedding_provider, chunking_strategy):
    """Adapter for the old process_book function"""
    pipeline = BookProcessingPipeline(
        book_service=book_service,
        embedding_provider=embedding_provider,
        chunking_strategy=chunking_strategy
    )
    await pipeline.process_book_from_url(book_url, chunk_size, session)
```

### Phase 5: Eliminate opret_bøger.py

#### 5.1. Check for any remaining imports
```bash
grep -r "from create_embeddings.opret_bøger import" --include="*.py" .
```

#### 5.2. Update remaining imports
For each file that imports from opret_bøger.py, update the imports to use the appropriate classes or adapters

#### 5.3. Remove opret_bøger.py
Once all references have been updated, remove the file

### Phase 6: Update Documentation

#### 6.1. Create/update markdown documentation
Create a new file `ELIMINATION_OF_OPRET_BOEGER.md` documenting the refactoring

## TODO Checklist

### Phase 1: Move URL Loading to Pipeline
- [ ] 1.1 Add load_urls_from_file method to BookProcessingPipeline
- [ ] 1.2 Create indlæs_urls_adapter in test_utils.py
- [ ] 1.3 Update book_processor_wrapper.py to use pipeline for URL loading
- [ ] 1.4 Remove indlæs_urls import from book_processor_wrapper.py
- [ ] 1.5 Update tests to use indlæs_urls_adapter
- [ ] 1.6 Run tests to verify functionality

### Phase 2: Make Pipeline Methods Public
- [ ] 2.1 Identify methods to make public
- [ ] 2.2 Rename methods (remove underscore prefix)
- [ ] 2.3 Update internal method calls
- [ ] 2.4 Update test adapters
- [ ] 2.5 Run tests to verify functionality

### Phase 3: Update BookProcessingApplication
- [ ] 3.1 Review BookProcessingApplication dependencies
- [ ] 3.2 Enhance error handling if needed
- [ ] 3.3 Run tests to verify functionality

### Phase 4: Remove process_book from opret_bøger.py
- [ ] 4.1 Identify all process_book calls
- [ ] 4.2 Update calls to use pipeline directly
- [ ] 4.3 Create process_book_adapter if needed
- [ ] 4.4 Run tests to verify functionality

### Phase 5: Eliminate opret_bøger.py
- [ ] 5.1 Check for remaining imports
- [ ] 5.2 Update remaining imports
- [ ] 5.3 Remove opret_bøger.py
- [ ] 5.4 Run tests to verify functionality

### Phase 6: Update Documentation
- [ ] 6.1 Create/update markdown documentation
- [ ] 6.2 Update comments in code
- [ ] 6.3 Review and finalize documentation

## Validation Strategy
After each phase:
1. Run unit tests: `python -m pytest`
2. Run specific test files directly: `python -m pytest path/to/test_file.py`
3. Manually run the application with a test input file

## Risk Assessment
- **Test failures**: Use adapter pattern to minimize impact on tests
- **Runtime errors**: Test thoroughly after each phase
- **Missing functionality**: Ensure all functions are accounted for before removal

This plan provides a structured approach to complete the transition from opret_bøger.py to the pipeline pattern, improving code quality while maintaining functionality.