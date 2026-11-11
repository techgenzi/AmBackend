import eventlet
eventlet.monkey_patch()

from main import app, socketio

application = app