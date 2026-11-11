from .. import socketio
from flask import request, session
from flask_socketio import join_room
import requests,os
auth_url = os.getenv("AUTH_URL", "https://ipssapi.techgenzi.com/users/auth/")
header_name = os.getenv("AUTH_HEADER_NAME", "Authorization")

connected_users =  {}

@socketio.on('connect')
def handle_connect(auth):
    # Manually verify token from auth object
    token = None
    if auth and 'token' in auth:
        token = auth['token']
    elif request.args.get('token'):
        token = request.args.get('token')

    if not token:
        print("Connection refused: No token provided")
        return False

    verify = requests.get(
        f"{auth_url}verify-token",
        headers={header_name: f"Bearer {token}"},
            timeout=5
    )
    # print(verify.json(),"verify_response")
    if verify.status_code != 200:
        print(f"Connection refused: {verify.json().get('msg', 'Unauthorized')}")
        return False

    current_user = verify.json()
    # print(current_user, "current_user")
    user_id = current_user.get('userid')

    if not user_id:
        print("Connection refused: Invalid token payload")
        return False

    room = f"user_{user_id}"
    connected_users[request.sid] = user_id
    join_room(room)
    print(f"User {user_id} connected (SID: {request.sid}) joined room {room}")


@socketio.on('disconnect')
def handle_disconnect():
    user_id = connected_users.pop(request.sid, None)
    if user_id:
        print(f"User {user_id} disconnected")