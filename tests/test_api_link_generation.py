import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src")

from bot.config import TUIC_PORT, VLESS_PLAIN_PORT, SERVER_IP

class TestApiLinkGeneration(unittest.TestCase):
    @patch('api.server.get_db_connection')
    def test_tuic_link_generation(self, mock_get_db):
        # Mock DB response
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn # FIX: Assign mock_conn to return value
        mock_cursor = MagicMock()
        mock_conn.execute.return_value = mock_cursor
        
        # Mock row data for TUIC user
        mock_row = {
            'uuid': 'test-uuid-123',
            'telegram_id': 123456,
            'username': 'testuser',
            'protocol': 'tuic',
            'is_active': 1,
            'created_at': '2023-01-01',
            'expiry_date': '2023-02-01',
            'daily_usage_bytes': 0,
            'data_limit_gb': 10
        }
        mock_cursor.fetchone.return_value = mock_row
        
        # Import the function to test
        from api.server import get_key_by_uuid
        
        # Call function
        result = get_key_by_uuid('test-uuid-123')
        
        # Verify link contains correct port and protocol
        self.assertIn(f":{TUIC_PORT}", result['vpn_link'])
        self.assertIn("tuic://", result['vpn_link'])
        self.assertIn("congestion_control=bbr", result['vpn_link'])
        print(f"TUIC Link Verified: {result['vpn_link']}")

    @patch('api.server.get_db_connection')
    def test_vless_plain_link_generation(self, mock_get_db):
        # Mock DB response
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn # FIX: Assign mock_conn to return value
        mock_cursor = MagicMock()
        mock_conn.execute.return_value = mock_cursor
        
        # Mock row data for Plain VLESS user
        mock_row = {
            'uuid': 'test-uuid-456',
            'telegram_id': 123456,
            'username': 'testuser',
            'protocol': 'vlessplain',
            'is_active': 1,
            'created_at': '2023-01-01',
            'expiry_date': '2023-02-01',
            'daily_usage_bytes': 0,
            'data_limit_gb': 10
        }
        mock_cursor.fetchone.return_value = mock_row
        
        # Import the function to test
        from api.server import get_key_by_uuid
        
        # Call function
        result = get_key_by_uuid('test-uuid-456')
        
        # Verify link contains correct port and protocol
        self.assertIn(f":{VLESS_PLAIN_PORT}", result['vpn_link'])
        self.assertIn("vless://", result['vpn_link'])
        self.assertIn("security=tls", result['vpn_link'])
        print(f"Plain VLESS Link Verified: {result['vpn_link']}")

if __name__ == '__main__':
    unittest.main()
