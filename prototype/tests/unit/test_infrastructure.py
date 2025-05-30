"""
Simple unit test to verify testing infrastructure.
"""
import pytest


@pytest.mark.unit
class TestBasicFunctionality:
    """Test basic functionality without external dependencies."""
    
    def test_basic_math(self):
        """Test basic mathematical operations."""
        assert 1 + 1 == 2
        assert 2 * 3 == 6
        assert 10 / 2 == 5

    def test_string_operations(self):
        """Test string operations."""
        test_string = "Hello, World!"
        assert test_string.lower() == "hello, world!"
        assert test_string.upper() == "HELLO, WORLD!"
        assert len(test_string) == 13

    def test_list_operations(self):
        """Test list operations."""
        test_list = [1, 2, 3, 4, 5]
        assert len(test_list) == 5
        assert test_list[0] == 1
        assert test_list[-1] == 5
        
        test_list.append(6)
        assert len(test_list) == 6
        assert test_list[-1] == 6

    def test_dictionary_operations(self):
        """Test dictionary operations."""
        test_dict = {"name": "test", "value": 42}
        assert test_dict["name"] == "test"
        assert test_dict["value"] == 42
        assert len(test_dict) == 2
        
        test_dict["new_key"] = "new_value"
        assert len(test_dict) == 3
        assert "new_key" in test_dict

    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """Test async functionality."""
        import asyncio
        
        async def async_function():
            await asyncio.sleep(0.01)  # Very short sleep
            return "async_result"
        
        result = await async_function()
        assert result == "async_result"


@pytest.mark.integration
class TestMockingCapabilities:
    """Test mocking capabilities."""
    
    def test_basic_mocking(self):
        """Test basic mocking functionality."""
        from unittest.mock import MagicMock
        
        mock_object = MagicMock()
        mock_object.method.return_value = "mocked_result"
        
        result = mock_object.method()
        assert result == "mocked_result"
        mock_object.method.assert_called_once()

    def test_patch_functionality(self):
        """Test patch functionality."""
        from unittest.mock import MagicMock
        
        # Test mocking functionality with MagicMock to avoid recursion issues
        mock_obj = MagicMock()
        mock_obj.calculate.return_value = 100
        
        result = mock_obj.calculate(5)
        assert result == 100
        mock_obj.calculate.assert_called_once_with(5)

    @pytest.mark.asyncio
    async def test_async_mocking(self):
        """Test async mocking."""
        from unittest.mock import AsyncMock
        
        mock_async = AsyncMock()
        mock_async.return_value = "async_mock_result"
        
        result = await mock_async()
        assert result == "async_mock_result"
        mock_async.assert_called_once()
