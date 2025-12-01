
import sys
import os
import asyncio
import uuid
from unittest.mock import MagicMock, AsyncMock, patch

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
print(f"DEBUG: sys.path: {sys.path}")


from bot.main import buy, handle_photo, handle_status
from db.database import init_db, get_user, get_user_stats
import services.ocr_service # Ensure module is loaded

# Mock data
MOCK_PROVIDER = "KBZ Pay"
MOCK_TID = "2000000000123456789"
MOCK_AMOUNT = 3000.0

async def test_full_flow():
    print("🚀 Starting Full Flow Test (Payment -> Key -> Status)...")
    
    # 1. Initialize DB
    init_db()
    print("✅ Database initialized")
    
    # 2. Mock User
    user_id = 111222333
    username = "flow_tester"
    
    # Mock Update/Context for buy command
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_user.username = username
    update.effective_user.first_name = "FlowTester"
    update.effective_user.language_code = "en"
    update.effective_user.is_premium = False
    update.message.reply_text = AsyncMock()
    update.message.reply_photo = AsyncMock()
    update.callback_query = None
    
    # Mock photo for handle_photo
    photo_mock = MagicMock()
    photo_mock.get_file = AsyncMock()
    update.message.photo = [photo_mock]
    
    context = MagicMock()
    context.user_data = {}
    
    # 3. Simulate /buy (to set protocol preference)
    print("\n📦 Step 1: User selects protocol...")
    # We'll just set it in user_data directly as if they clicked a button
    context.user_data['protocol'] = 'vless'
    print("   User selected: VLESS")
    
    # 4. Simulate Payment (handle_photo)
    print("\n💸 Step 2: User sends payment slip...")
    
    # Mock the photo file download and OCR/Validation services
    import bot.main
    import services.ocr_service
    import services.payment_validator
    import bot.config_manager
    import tempfile
    import os
    
    # Manual patching
    original_nsfw = bot.main.get_nsfw_detector
    bot.main.get_nsfw_detector = MagicMock(return_value=None)
    
    # Mock OCR module
    mock_ocr_module = MagicMock()
    mock_ocr_module.ocr_service.extract_text.return_value = ["KBZ Pay", "Transfer Successful", f"Transaction ID: {MOCK_TID}", f"Amount: {MOCK_AMOUNT} MMK"]
    
    # Mock Payment Validator module
    mock_validator_module = MagicMock()
    mock_validator_module.payment_validator.validate_receipt.return_value = {
        'provider': MOCK_PROVIDER,
        'transaction_id': MOCK_TID,
        'amount': MOCK_AMOUNT,
        'timestamp': '2023-01-01 12:00:00'
    }
    
    try:
        with patch.dict(sys.modules, {
            'services.ocr_service': mock_ocr_module,
            'services.payment_validator': mock_validator_module
        }), \
        patch('tempfile.NamedTemporaryFile') as mock_temp, \
        patch('os.path.exists') as mock_exists, \
        patch('os.unlink') as mock_unlink, \
        patch.object(bot.config_manager, 'add_user_to_config') as mock_config_update:
            
            # Mock temp file
            mock_temp.return_value.__enter__.return_value.name = "/tmp/mock_slip.jpg"
            mock_exists.return_value = True
            
            # Debug
            print(f"DEBUG: bot.main.get_nsfw_detector is mock? {isinstance(bot.main.get_nsfw_detector, MagicMock)}")
            
            # Execute handle_photo
            try:
                await handle_photo(update, context)
            except Exception as e:
                print(f"   ❌ handle_photo raised exception: {e}")
                import traceback
                traceback.print_exc()
    finally:
        # Restore manual patch
        bot.main.get_nsfw_detector = original_nsfw 
        
    # Verify success message
    # We expect multiple calls: "Verifying...", "Payment Verified!", "Key ready!"
    calls = update.message.reply_text.call_args_list
    payment_verified = False
    key_generated = False
    
    print(f"   DEBUG: reply_text calls ({len(calls)}):")
    for call in calls:
        msg = call[0][0]
        print(f"     - {msg[:50]}...") # Print first 50 chars
        if "Payment Verified" in msg:
            payment_verified = True
            print("   ✅ Payment verified message received")
        if "Your VLESS+REALITY key is ready" in msg:
            key_generated = True
            print("   ✅ Key generation message received")
                
            print("   ❌ Failed to generate key")
            return

    # 5. Verify DB State
    print("\n🗄️ Step 3: Verifying Database...")
    stats = get_user_stats(user_id)
    if not stats:
        print("   ❌ No stats found for user")
        return
        
    user_stat = stats[0]
    print(f"   User UUID: {user_stat['uuid']}")
    print(f"   Protocol: {user_stat['protocol']}")
    print(f"   Active: {user_stat['is_active']}")
    
    if user_stat['protocol'] != 'vless':
        print(f"   ❌ Wrong protocol in DB: {user_stat['protocol']}")
        return
        
    print("   ✅ Database record looks correct")

    # 6. Simulate /status
    print("\n📊 Step 4: User checks status...")
    
    # Reset mock for clarity
    update.message.reply_text.reset_mock()
    
    await handle_status(update, context)
    
    # Verify status output
    args, _ = update.message.reply_text.call_args
    status_msg = args[0]
    
    print("   Status Message Received:")
    print("   ------------------------")
    print(status_msg)
    print("   ------------------------")
    
    if "Active" in status_msg and "VLESS+REALITY" in status_msg:
        print("\n✅ Full flow test passed! Status command works correctly.")
    else:
        print("\n❌ Status command output incorrect.")

if __name__ == "__main__":
    asyncio.run(test_full_flow())
