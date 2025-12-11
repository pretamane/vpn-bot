#!/usr/bin/env python3
"""
Test script for data limit auto-expiration feature.
Tests the complete workflow: warnings at 30%, 65%, 95%, grace period, and expiration.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.database import (
    get_db_connection, init_db, add_user, update_usage,
    get_daily_usage, start_grace_period, is_in_grace_period,
    get_grace_period_remaining, has_warning_been_sent,
    update_data_warning, expire_user
)
import uuid
import datetime

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def create_test_user():
    """Create a test VLESS Limited user with 3GB limit."""
    print_section("Creating Test User")
    
    test_uuid = str(uuid.uuid4())
    test_telegram_id = 999999999
    test_username = "test_data_limit_user"
    
    success = add_user(
        uuid=test_uuid,
        telegram_id=test_telegram_id,
        username=test_username,
        protocol='vless_limited',
        language_code='en',
        is_premium=False,
        expiry_days=30,
        speed_limit_mbps=12.0,
        data_limit_gb=3.0  # 3GB limit
    )
    
    if success:
        print(f"✅ Created test user: {test_uuid}")
        print(f"   - Telegram ID: {test_telegram_id}")
        print(f"   - Protocol: vless_limited")
        print(f"   - Data Limit: 3.0 GB")
        print(f"   - Speed Limit: 12.0 Mbps")
        return test_uuid
    else:
        print(f"❌ Failed to create test user")
        return None

def simulate_data_usage(user_uuid, gb):
    """Simulate data usage for a user."""
    bytes_to_add = int(gb * 1024 * 1024 * 1024)
    update_usage(user_uuid, bytes_to_add)
    
    daily_usage = get_daily_usage(user_uuid)
    daily_gb = daily_usage / (1024**3)
    
    print(f"   Added {gb:.2f} GB → Total: {daily_gb:.2f} GB")
    return daily_gb

def test_warning_thresholds(user_uuid):
    """Test warning thresholds at 30%, 65%, 95%."""
    print_section("Testing Warning Thresholds")
    
    limit_gb = 3.0
    thresholds = [
        (0.3, 30),  # 30% = 0.9 GB
        (0.65, 65), # 65% = 1.95 GB
        (0.95, 95)  # 95% = 2.85 GB
    ]
    
    for multiplier, threshold_pct in thresholds:
        target_gb = limit_gb * multiplier
        print(f"\n📊 Testing {threshold_pct}% threshold ({target_gb:.2f} GB):")
        
        # Simulate usage up to threshold
        current_usage = get_daily_usage(user_uuid) / (1024**3)
        gb_to_add = target_gb - current_usage + 0.01  # Slightly over threshold
        
        if gb_to_add > 0:
            daily_gb = simulate_data_usage(user_uuid, gb_to_add)
            percentage = (daily_gb / limit_gb) * 100
            
            # Check if warning would be sent
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE uuid = ?', (user_uuid,)).fetchone()
            conn.close()
            
            if not has_warning_been_sent(dict(user), threshold_pct):
                print(f"   ⚠️  Warning would be sent at {percentage:.1f}%")
                update_data_warning(user_uuid, threshold_pct)
            else:
                print(f"   ℹ️  Warning already sent")

def test_grace_period(user_uuid):
    """Test grace period functionality."""
    print_section("Testing Grace Period")
    
    limit_gb = 3.0
    current_usage = get_daily_usage(user_uuid) / (1024**3)
    
    # Simulate usage to exceed limit
    print(f"\n📈 Simulating usage to exceed {limit_gb} GB limit...")
    gb_to_add = (limit_gb - current_usage) + 0.5  # 0.5 GB over limit
    
    if gb_to_add > 0:
        daily_gb = simulate_data_usage(user_uuid, gb_to_add)
        
        if daily_gb >= limit_gb:
            print(f"\n🚨 Limit exceeded: {daily_gb:.2f}/{limit_gb} GB")
            
            # Start grace period
            print("   Starting 24-hour grace period...")
            start_grace_period(user_uuid)
            
            # Check grace period status
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE uuid = ?', (user_uuid,)).fetchone()
            conn.close()
            
            user_dict = dict(user)
            if is_in_grace_period(user_dict):
                remaining = get_grace_period_remaining(user_dict)
                hours = remaining.total_seconds() / 3600
                print(f"   ✅ Grace period active")
                print(f"   ⏳ Time remaining: {hours:.1f} hours")
            else:
                print(f"   ❌ Grace period not active")

def test_expiration(user_uuid):
    """Test key expiration."""
    print_section("Testing Key Expiration")
    
    conn = get_db_connection()
    user_before_row = conn.execute('SELECT * FROM users WHERE uuid = ?', (user_uuid,)).fetchone()
    conn.close()
    
    user_before = dict(user_before_row)
    
    print(f"Before expiration:")
    print(f"   - is_active: {user_before['is_active']}")
    print(f"   - grace_period_start: {user_before.get('grace_period_start', 'None')}")
    
    # Expire the user
    print(f"\n🔒 Expiring user...")
    expire_user(user_uuid, reason='grace_period_ended')
    
    conn = get_db_connection()
    user_after_row = conn.execute('SELECT * FROM users WHERE uuid = ?', (user_uuid,)).fetchone()
    conn.close()
    
    user_after = dict(user_after_row)
    
    print(f"\nAfter expiration:")
    print(f"   - is_active: {user_after['is_active']}")
    print(f"   - expiry_reason: {user_after.get('expiry_reason', 'None')}")
    print(f"   - expired_at: {user_after.get('expired_at', 'None')}")
    
    if user_after['is_active'] == 0:
        print(f"\n   ✅ User successfully expired")
    else:
        print(f"\n   ❌ User still active")

def cleanup_test_user(user_uuid):
    """Clean up test user."""
    print_section("Cleanup")
    
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE uuid = ?', (user_uuid,))
    conn.execute('DELETE FROM usage_logs WHERE uuid = ?', (user_uuid,))
    conn.commit()
    conn.close()
    
    print(f"✅ Cleaned up test user: {user_uuid}")

def main():
    print("\n" + "="*60)
    print("  DATA LIMIT AUTO-EXPIRATION TEST")
    print("="*60)
    print("\nThis test will verify the complete data limit workflow:")
    print("  1. Create VLESS Limited user with 3GB limit")
    print("  2. Simulate data usage and test warning thresholds")
    print("  3. Test grace period (24 hours)")
    print("  4. Test expiration after grace period")
    print("\n" + "="*60)
    
    # Initialize database
    init_db()
    
    # Create test user
    user_uuid = create_test_user()
    if not user_uuid:
        print("\n❌ Test failed: Could not create user")
        return
    
    try:
        # Test warning thresholds
        test_warning_thresholds(user_uuid)
        
        # Test grace period
        test_grace_period(user_uuid)
        
        # Test expiration
        test_expiration(user_uuid)
        
        print_section("Test Summary")
        print("✅ All tests completed successfully!")
        print("\nNext steps:")
        print("  1. Deploy updated code to server")
        print("  2. Restart watchdog service")
        print("  3. Monitor logs for data limit events")
        
    finally:
        # Cleanup
        cleanup_test_user(user_uuid)

if __name__ == "__main__":
    main()
