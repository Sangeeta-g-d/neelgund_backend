import logging
from firebase_admin import messaging
logger = logging.getLogger(__name__)
from auth_api.models import CustomUser

def send_fcm_notification(user, title, body, data=None):
    """
    Send FCM notification to all user's devices
    """
    print("\n" + "="*50)
    print("🔔 STARTING FCM NOTIFICATION PROCESS")
    print("="*50)
    print(f"📧 User Email: {user.email}")
    print(f"📱 User ID: {user.id}")
    print(f"📝 Title: {title}")
    print(f"💬 Body: {body}")
    print(f"📦 Data: {data}")
    
    device_tokens = user.device_tokens.all()
    print(f"\n🔍 Querying device tokens for user...")
    print(f"✅ Found {device_tokens.count()} device token(s)")
    
    if not device_tokens.exists():
        print("❌ No device tokens found for this user")
        logger.info(f"No device tokens found for user {user.email}")
        print("="*50 + "\n")
        return
    
    print("\n📋 Device Details:")
    for idx, device in enumerate(device_tokens, 1):
        print(f"  Device {idx}:")
        print(f"    - Type: {device.device_type}")
        print(f"    - Token (first 20 chars): {device.token[:20]}...")
        print(f"    - Created: {device.created_at}")
        print(f"    - Updated: {device.updated_at}")
    
    successful_sends = 0
    failed_tokens = []
    
    print("\n📤 Sending notifications...")
    for idx, device in enumerate(device_tokens, 1):
        print(f"\n  Attempting send {idx}/{device_tokens.count()}:")
        print(f"    Device Type: {device.device_type}")
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                token=device.token,
            )
            
            print(f"    📨 Calling Firebase messaging.send()...")
            response = messaging.send(message)
            successful_sends += 1
            print(f"    ✅ SUCCESS! Response: {response}")
            logger.info(f"Successfully sent notification to {device.device_type} device: {response}")
            
        except messaging.UnregisteredError as e:
            # Token is invalid, delete it
            print(f"    ⚠️  UNREGISTERED TOKEN ERROR")
            print(f"    ❌ Token is invalid/unregistered: {str(e)}")
            print(f"    🗑️  Marking token for deletion...")
            logger.warning(f"Invalid token for {user.email}, deleting: {device.token}")
            failed_tokens.append(device)
            
        except messaging.SenderIdMismatchError as e:
            print(f"    ⚠️  SENDER ID MISMATCH ERROR")
            print(f"    ❌ Error: {str(e)}")
            logger.error(f"Sender ID mismatch for {user.email}: {str(e)}")
            
        except messaging.InvalidArgumentError as e:
            print(f"    ⚠️  INVALID ARGUMENT ERROR")
            print(f"    ❌ Error: {str(e)}")
            logger.error(f"Invalid argument for {user.email}: {str(e)}")
            
        except Exception as e:
            print(f"    ⚠️  UNEXPECTED ERROR")
            print(f"    ❌ Error Type: {type(e).__name__}")
            print(f"    ❌ Error Message: {str(e)}")
            logger.error(f"Error sending notification to {user.email}: {str(e)}")
    
    # Clean up invalid tokens
    if failed_tokens:
        print(f"\n🗑️  Cleaning up {len(failed_tokens)} invalid token(s)...")
        for device in failed_tokens:
            print(f"    Deleting token: {device.token[:20]}...")
            device.delete()
            print(f"    ✅ Deleted")
    
    print(f"\n📊 SUMMARY:")
    print(f"    Total Devices: {device_tokens.count()}")
    print(f"    Successful Sends: {successful_sends}")
    print(f"    Failed Sends: {device_tokens.count() - successful_sends}")
    print(f"    Tokens Deleted: {len(failed_tokens)}")
    
    logger.info(f"Sent {successful_sends} notifications to {user.email}")
    print("="*50 + "\n")




def send_fcm_notification_to_all_agents(title, body, data=None):
    """
    Send FCM notification to all approved agents
    """
    print("\n" + "="*50)
    print("🔔 SENDING NOTIFICATION TO ALL AGENTS")
    print("="*50)
    
    # Get all approved agents (excluding superusers/staff)
    agents = CustomUser.objects.filter(
        approved=True,
        is_staff=False,
        is_superuser=False
    )
    
    total_agents = agents.count()
    print(f"👥 Found {total_agents} approved agent(s)")
    
    if total_agents == 0:
        print("❌ No approved agents found")
        print("="*50 + "\n")
        return
    
    total_devices = 0
    successful_sends = 0
    failed_sends = 0
    
    for agent in agents:
        print(f"\n📧 Processing agent: {agent.email} ({agent.full_name})")
        
        device_tokens = agent.device_tokens.all()
        agent_device_count = device_tokens.count()
        total_devices += agent_device_count
        
        print(f"   📱 Devices: {agent_device_count}")
        
        if not device_tokens.exists():
            print(f"   ⚠️  No device tokens for this agent")
            continue
        
        failed_tokens = []
        
        for idx, device in enumerate(device_tokens, 1):
            print(f"   📤 Sending to device {idx}/{agent_device_count} ({device.device_type})...")
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    data=data or {},
                    token=device.token,
                )
                
                response = messaging.send(message)
                successful_sends += 1
                print(f"      ✅ SUCCESS: {response}")
                logger.info(f"Sent notification to {agent.email} - {device.device_type}: {response}")
                
            except messaging.UnregisteredError:
                print(f"      ⚠️  UNREGISTERED TOKEN - marking for deletion")
                logger.warning(f"Invalid token for {agent.email}, deleting: {device.token}")
                failed_tokens.append(device)
                failed_sends += 1
                
            except Exception as e:
                print(f"      ❌ ERROR: {type(e).__name__} - {str(e)}")
                logger.error(f"Error sending notification to {agent.email}: {str(e)}")
                failed_sends += 1
        
        # Clean up invalid tokens
        if failed_tokens:
            print(f"   🗑️  Deleting {len(failed_tokens)} invalid token(s)...")
            for device in failed_tokens:
                device.delete()
    
    print(f"\n📊 NOTIFICATION SUMMARY:")
    print(f"    Total Agents: {total_agents}")
    print(f"    Total Devices: {total_devices}")
    print(f"    Successful Sends: {successful_sends}")
    print(f"    Failed Sends: {failed_sends}")
    print("="*50 + "\n")
    
    logger.info(f"Bulk notification sent to {total_agents} agents - Success: {successful_sends}, Failed: {failed_sends}")
