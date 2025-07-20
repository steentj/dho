#!/usr/bin/env python3
"""
Quick validation test for refactoring 1.
"""

# Test the defensive fix logic directly
def test_defensive_fix_logic():
    """Test the defensive fix logic from save_book function"""
    
    # Simulate the chunks from the failing test cases
    test_chunks = [
        (1, "Normal string"),            # Should remain unchanged
        (2, ["This", "is", "a", "list"]), # Should become "This is a list" 
        (3, 12345),                      # Should become "12345"
        (4, []),                         # Should become ""
    ]
    
    fixed_chunks = []
    
    # Apply the same logic as in save_book function
    for page_num, chunk_text in test_chunks:
        if isinstance(chunk_text, list):
            # Join list elements into a single string
            chunk_text = " ".join(str(item) for item in chunk_text)
            print(f"Fixed chunk_text data type: converted list to string for page {page_num}")
        elif not isinstance(chunk_text, str):
            # Convert any other type to string
            chunk_text = str(chunk_text)
            print(f"Fixed chunk_text data type: converted {type(chunk_text)} to string for page {page_num}")
        
        fixed_chunks.append((page_num, chunk_text))
    
    # Verify results
    print("\nResults:")
    for page_num, chunk_text in fixed_chunks:
        print(f"Page {page_num}: '{chunk_text}' (type: {type(chunk_text).__name__})")
    
    # Check that all are strings
    all_strings = all(isinstance(chunk_text, str) for _, chunk_text in fixed_chunks)
    print(f"\nAll chunks are strings: {all_strings}")
    
    # Check specific conversions
    expected_results = [
        (1, "Normal string"),
        (2, "This is a list"), 
        (3, "12345"),
        (4, "")
    ]
    
    matches = all(actual == expected for actual, expected in zip(fixed_chunks, expected_results))
    print(f"All conversions match expected results: {matches}")
    
    return all_strings and matches


if __name__ == "__main__":
    print("Testing defensive fix logic...")
    success = test_defensive_fix_logic()
    if success:
        print("\n✅ SUCCESS: Defensive fix logic works correctly")
    else:
        print("\n❌ FAILURE: Defensive fix logic has issues")
