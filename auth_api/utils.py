import requests
from django.conf import settings

def send_otp_via_smsalert(phone_number, otp):
    url = "https://www.smsalert.co.in/api/push.json"
    message = f"Your login OTP is {otp}. It is valid for 5 minutes. - Team Support"

    # ⚠️ Important: SMS Alert requires sender ID to be 6 uppercase characters (e.g., NEELGD)
    # It cannot be an email or number
    payload = {
        "user": settings.SMS_ALERT_USERNAME,
        "password": settings.SMS_ALERT_PASSWORD,
        "sender": settings.SMS_ALERT_SENDER_ID,
        "mobile": phone_number,  # ✅ use 'mobile', not 'to'
        "message": message,
        "type": "3",  # ✅ transactional route (3 = transactional, 1 = promotional)
    }

    print(f"🌐 Sending POST request to SMS Alert with payload: {payload}")

    try:
        response = requests.post(url, data=payload)
        print(f"📡 SMS Alert HTTP Status: {response.status_code}")
        print(f"📨 SMS Alert Raw Response: {response.text}")

        try:
            return response.json()
        except Exception:
            return {"status": "error", "message": "Invalid response from SMS Alert"}

    except Exception as e:
        print(f"❌ Error while sending OTP: {e}")
        return {"status": "error", "message": str(e)}
