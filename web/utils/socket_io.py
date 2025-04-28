from flask_socketio import SocketIO

def init_socketio(app):
    """Initialize SocketIO with the Flask app"""
    socketio = SocketIO(app, 
        cors_allowed_origins="*", 
        allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Origin", "Access-Control-Allow-Headers"],
        transports=['websocket'],
        async_mode='eventlet',
        message_queue='redis://localhost:6379/0',
        channel='socketio'
    )
    return socketio