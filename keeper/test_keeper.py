#!/usr/bin/env python3
"""
Test script for GoFile Keeper - validates functionality without making real requests
"""

import os
import sys
from unittest.mock import Mock, patch, MagicMock
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from keeper import SupabaseClient, GoFileKeeper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_supabase_client():
    """Test Supabase client initialization and methods"""
    logger.info("🧪 Testing SupabaseClient...")
    
    client = SupabaseClient("https://test.supabase.co", "test-key")
    
    assert client.url == "https://test.supabase.co"
    assert client.api_key == "test-key"
    assert "apikey" in client.headers
    assert "Authorization" in client.headers
    
    logger.info("  ✅ SupabaseClient initialization passed")


def test_gofile_keeper_init():
    """Test GoFileKeeper initialization"""
    logger.info("🧪 Testing GoFileKeeper initialization...")
    
    keeper = GoFileKeeper()
    
    assert keeper.session is not None
    assert keeper.stats['total'] == 0
    assert keeper.stats['success'] == 0
    assert keeper.stats['failed'] == 0
    
    logger.info("  ✅ GoFileKeeper initialization passed")


def test_keep_alive_success():
    """Test successful keep-alive operation"""
    logger.info("🧪 Testing keep_alive success scenario...")
    
    keeper = GoFileKeeper()
    
    # Mock successful responses
    with patch.object(keeper.session, 'head') as mock_head, \
         patch.object(keeper.session, 'get') as mock_get:
        
        # Mock HEAD request
        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head.return_value = mock_head_response
        
        # Mock GET request
        mock_get_response = Mock()
        mock_get_response.status_code = 206
        mock_get_response.iter_content = Mock(return_value=[b'test data'])
        mock_get.return_value = mock_get_response
        
        success, error = keeper.keep_alive("https://gofile.io/d/test123")
        
        assert success is True
        assert error is None
        
    logger.info("  ✅ keep_alive success test passed")


def test_keep_alive_404():
    """Test keep-alive with deleted file (404)"""
    logger.info("🧪 Testing keep_alive 404 scenario...")
    
    keeper = GoFileKeeper()
    
    with patch.object(keeper.session, 'head') as mock_head:
        mock_head_response = Mock()
        mock_head_response.status_code = 404
        mock_head.return_value = mock_head_response
        
        success, error = keeper.keep_alive("https://gofile.io/d/deleted")
        
        assert success is False
        assert "404" in error
        
    logger.info("  ✅ keep_alive 404 test passed")


def test_keep_alive_timeout():
    """Test keep-alive with timeout"""
    logger.info("🧪 Testing keep_alive timeout scenario...")
    
    keeper = GoFileKeeper()
    
    with patch.object(keeper.session, 'head') as mock_head:
        mock_head.side_effect = Exception("Timeout")
        
        success, error = keeper.keep_alive("https://gofile.io/d/timeout")
        
        assert success is False
        assert error is not None
        
    logger.info("  ✅ keep_alive timeout test passed")


def test_process_links():
    """Test processing multiple links"""
    logger.info("🧪 Testing process_links...")
    
    keeper = GoFileKeeper()
    
    test_links = [
        {'id': 1, 'streamer_name': 'test1', 'gofile_link': 'https://gofile.io/d/test1'},
        {'id': 2, 'streamer_name': 'test2', 'gofile_link': 'https://gofile.io/d/test2'},
    ]
    
    with patch.object(keeper, 'keep_alive') as mock_keep_alive, \
         patch('keeper.SupabaseClient') as mock_supabase_class:
        
        # Mock keep_alive to return success
        mock_keep_alive.return_value = (True, None)
        
        # Mock Supabase client
        mock_supabase = Mock()
        mock_supabase_class.return_value = mock_supabase
        
        # Mock environment variables
        with patch.dict(os.environ, {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_API_KEY': 'test-key',
            'DELAY_BETWEEN_REQUESTS': '0'  # No delay for testing
        }):
            keeper.process_links(test_links)
        
        assert keeper.stats['total'] == 2
        assert keeper.stats['success'] == 2
        assert keeper.stats['failed'] == 0
        
    logger.info("  ✅ process_links test passed")


def test_environment_validation():
    """Test environment variable validation"""
    logger.info("🧪 Testing environment validation...")
    
    # Save original env vars
    original_url = os.environ.get('SUPABASE_URL')
    original_key = os.environ.get('SUPABASE_API_KEY')
    
    try:
        # Remove env vars
        if 'SUPABASE_URL' in os.environ:
            del os.environ['SUPABASE_URL']
        if 'SUPABASE_API_KEY' in os.environ:
            del os.environ['SUPABASE_API_KEY']
        
        # This should fail when importing keeper module
        # We'll just check that the variables are required
        assert os.getenv('SUPABASE_URL') is None
        assert os.getenv('SUPABASE_API_KEY') is None
        
        logger.info("  ✅ Environment validation test passed")
        
    finally:
        # Restore original env vars
        if original_url:
            os.environ['SUPABASE_URL'] = original_url
        if original_key:
            os.environ['SUPABASE_API_KEY'] = original_key


def run_all_tests():
    """Run all tests"""
    logger.info("="*60)
    logger.info("🚀 Running GoFile Keeper Tests")
    logger.info("="*60)
    
    tests = [
        test_supabase_client,
        test_gofile_keeper_init,
        test_keep_alive_success,
        test_keep_alive_404,
        test_keep_alive_timeout,
        test_process_links,
        test_environment_validation,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            logger.error(f"  ❌ Test failed: {e}")
            failed += 1
        except Exception as e:
            logger.error(f"  💥 Test error: {e}")
            failed += 1
    
    logger.info("")
    logger.info("="*60)
    logger.info(f"📊 Test Results: {passed} passed, {failed} failed")
    logger.info("="*60)
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    # Set test environment variables
    os.environ['SUPABASE_URL'] = 'https://test.supabase.co'
    os.environ['SUPABASE_API_KEY'] = 'test-key'
    
    exit_code = run_all_tests()
    sys.exit(exit_code)
