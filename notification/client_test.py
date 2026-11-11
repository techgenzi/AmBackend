#!/usr/bin/env python3
"""
WebSocket Debug Script - Shows detailed error messages
"""

import socketio
import time
import sys
import traceback

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc4MDY0MTQ4NiwianRpIjoiNTI0NTlkOTItMzExYi00ODEwLWFhNTAtMDRkMDYxNmI4NjZmIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6IlN1cnlhIiwibmJmIjoxNzgwNjQxNDg2LCJleHAiOjE3ODA3Mjc4ODYsInVzZXJuYW1lIjoiU3VyeWEiLCJjb250cm9saWQiOjEsInByb2plY3RpZCI6IkNSTSIsImZpbnlyIjoiMjMtMjQiLCJmaW55cl9pZCI6MTY0OTY4MjIwNDc3OCwiY29tcGNvZGUiOiJDUk0iLCJkaXNwbGF5IjoiQ1JNIiwiY29tcG5hbWUiOiJDUk0iLCJiYnJhbmNoIjoiQ29pbWJhdG9yZSIsImFkZHJlc3MiOiIiLCJnc3RubyI6bnVsbCwiY29tcGFueV9pZCI6MjgsInRlbmFudF9pZCI6MTIzLCJhdHRyaWJ1dGVzIjp7ImxvZ28iOiJodHRwczovL3NncDEuZGlnaXRhbG9jZWFuc3BhY2VzLmNvbS9mcmVzaHZvaWNlL2RvY3MvMjAyNS8xMi83MTU3In0sIm5vdGlmeV9hY2Nfc2lkIjoiVEdaQUNDU0lEY2ExMWQ2YzM3MDFhMiIsIm5vdGlmeV9hY2NfYXV0aF90b2tlbiI6IlZfbS1BWDR0VXE1NG5SdGlzNUZJLXVGWWJmUG1DYUJnNXNUd3BYX28xNktSc0gxenpVM09jX2pOOFc2U1U4NmE5U3h4aHpEMWJGN2N0R2VuY3pwRFliZWN6RHUteXFVdTIzdUo5OVpMNGJ3OUF3dmpjV2M4LUtONkFFVlRYQXRzT0FTVzgzVkVRdGJ1NWRtZTRmSkg5UmllVHFOdkRLam5QUFJ3T05HbWRrQSIsInVzZXJpZCI6MTU4MjUzNjk3NDQxMCwiZW1wX2lkIjpudWxsLCJ1c2VyX3JvbGUiOiJBZG1pbiJ9.yT9hm5MpJdQPb-4FMg-vQTLju4AG66F1v0wFgO0OgA8"
print("=" * 70)
print("🔍 WebSocket Connection Debug")
print("=" * 70)
print()

# Step 1: Check if domain is accessible
print("📍 Step 1: Check if domain is accessible")
print("-" * 70)

# import requests
# url = "http://127.0.0.1:5000/socket.io/?transport=polling"
# url = "https://ipssapi.techgenzi.com"
# try:
#     print("Testing HTTP connectivity to domain...")
#     response = requests.get(url, timeout=5)
#     print(url, "is reachable")
#     print(f"✅ HTTP GET Status: {response.status_code}")
#     print(f"   Response length: {len(response.text)} bytes")
#     if response.status_code == 200:
#         print(f"   Response preview: {response.text[:200]}")
# except requests.exceptions.ConnectionError as e:
#     print(f"❌ Cannot reach domain: {e}")
#     print("   → Check if domain is accessible: ping am-dev.techgenzi.com")
#     sys.exit(1)
# except requests.exceptions.Timeout as e:
#     print(f"❌ Connection timeout: {e}")
#     print("   → Domain is slow or unreachable")
#     sys.exit(1)
# except Exception as e:
#     print(f"❌ HTTP request failed: {e}")
#
# print()

# Step 2: Check token validity
print("📍 Step 2: Check token validity")
print("-" * 70)

import jwt
from datetime import datetime

try:
    decoded = jwt.decode(TOKEN, options={"verify_signature": False})
    print(f"✅ Token decoded successfully")
    print(f"   Username: {decoded.get('username')}")
    print(f"   User ID: {decoded.get('userid')}")
    print(f"   Company ID: {decoded.get('company_id')}")

    # Check expiration
    exp_time = decoded.get('exp')
    if exp_time:
        from datetime import datetime

        exp_date = datetime.fromtimestamp(exp_time)
        now = datetime.now()
        if exp_date < now:
            print(f"   ❌ Token EXPIRED on {exp_date}")
            print(f"      Generate a fresh token!")
            sys.exit(1)
        else:
            time_left = (exp_date - now).total_seconds() / 3600
            print(f"   ✅ Token valid for {time_left:.1f} more hours")
except Exception as e:
    print(f"❌ Token decode error: {e}")

print()

# Step 3: Test WebSocket connection with detailed logging
print("📍 Step 3: Attempt WebSocket connection")
print("-" * 70)

sio = socketio.Client(logger=True, engineio_logger=True)

connection_info = {
    "connected": False,
    "error": None,
    "transport": None
}


@sio.on("connect")
def on_connect():
    connection_info["connected"] = True
    print(f"✅ Connected! Socket ID: {sio.sid}")
    sio.disconnect()


@sio.on("connect_error")
def on_connect_error(error):
    connection_info["error"] = str(error)
    print(f"❌ Connect error: {error}")


@sio.on("engine_connect_error")
def on_engine_connect_error(error):
    connection_info["error"] = str(error)
    print(f"❌ Engine connect error: {error}")


@sio.on("disconnect")
def on_disconnect():
    print("🔌 Disconnected")


try:
    print("⏳ Connecting with WebSocket + Polling fallback...")
    # print(f"   URL: https://am-dev.techgenzi.com")
    # print(f"   Auth token: {TOKEN[:40]}...")
    print()

    sio.connect(
        "https://ipssapi.techgenzi.com",
        auth={"token": TOKEN},
        transports=["polling", "websocket"],  # Allow both polling and websocket
        wait_timeout=12,
        socketio_path="socket.io"
    )
    # sio.connect(
    #     "https://am-dev.techgenzi.com",
    #     auth={"token": TOKEN},
    #     transports=["websocket"],  # ONLY websocket
    #     wait_timeout=10,
    #     socketio_path="socket.io"
    # )
    # Wait a bit
    time.sleep(3)

    if connection_info["connected"]:
        print("✅ Connection successful!")
    else:
        print("⚠️  Connection timed out")

except Exception as e:
    print(f"❌ Connection exception: {type(e).__name__}")
    print(f"   Message: {e}")
    print()
    print("Full traceback:")
    traceback.print_exc()
    print()

    connection_info["error"] = str(e)

print()
print("=" * 70)
print("🔍 Diagnostics Summary")
print("=" * 70)

if connection_info["connected"]:
    print("✅ WebSocket is working!")
else:
    print("❌ WebSocket connection failed")
    print()

    error_msg = connection_info["error"] or "Unknown error"

    print("💡 Troubleshooting based on error:")
    print(error_msg)

    if "Connection error" in error_msg or "Connection refused" in error_msg:
        print("   → Service is not running or Nginx is not forwarding")
        print("   → Check:")
        print("      1. docker ps | grep notification")
        print("      2. docker logs nginx-reverse-proxy | tail -20")
        print("      3. docker logs notification-service | tail -20")

    elif "Invalid" in error_msg or "Unauthorized" in error_msg:
        print("   → Token is invalid or rejected by auth service")
        print("   → Check:")
        print("      1. Is token expired?")
        print("      2. Generate a fresh token from auth service")
        print("      3. Verify token with: curl AUTH_URL/verify-token -H 'Authorization: Bearer TOKEN'")

    elif "Timeout" in error_msg or "timeout" in error_msg:
        print("   → Connection timeout - service is slow or unreachable")
        print("   → Check:")
        print("      1. Is domain reachable? curl https://am-dev.techgenzi.com")
        print("      2. Check network connectivity")
        print("      3. Increase timeout in connect() call")

    elif "SSL" in error_msg or "certificate" in error_msg:
        print("   → SSL/HTTPS certificate issue")
        print("   → Check:")
        print("      1. curl -v https://am-dev.techgenzi.com (check certificate)")
        print("      2. Try with verify_ssl=False (dev only)")

    elif "404" in error_msg:
        print("   → Socket.io endpoint not found")
        print("   → Check:")
        print("      1. URL is correct: https://am-dev.techgenzi.com/socket.io")
        print("      2. Nginx /socket.io location block is configured")
        print("      3. Backend is serving socket.io")

    else:
        print(f"   → Unknown error: {error_msg}")
        print("   → Check all logs and try again")

print()