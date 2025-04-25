import { io, Socket } from 'socket.io-client'

let socketInstance: Socket | null = null

interface SocketError {
  message: string;
  code?: string;
}

interface SocketRequest {
  method: string;
  url: string;
}

interface SocketResponse {
  statusCode: number;
}

// Create a socket connection with debugging
export const createSocketConnection = (url: string): Socket => {
  if (socketInstance) {
    console.log('Reusing existing socket connection')
    return socketInstance
  }

  console.log(`Creating new WebSocket connection to ${url}`)
  
  socketInstance = io(url, {
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    timeout: 20000,
    autoConnect: true,
    transports: ['websocket'],
    upgrade: false,
    forceNew: false,
    withCredentials: true,
    extraHeaders: {
      'Access-Control-Allow-Origin': 'http://127.0.0.1:5173',
      'Access-Control-Allow-Credentials': 'true'
    }
  })
  
  // Add event listeners for debugging
  socketInstance.on('connect', () => {
    console.log('Socket connected')
  })
  
  socketInstance.on('disconnect', (reason) => {
    console.log(`Socket disconnected: ${reason}`)
    if (reason === 'io server disconnect') {
      // Server initiated disconnect, try to reconnect
      setTimeout(() => {
        socketInstance?.connect()
      }, 1000)
    }
  })
  
  socketInstance.on('connect_error', (error) => {
    console.error('Socket connection error:', error)
  })
  
  socketInstance.on('error', (error) => {
    console.error('Socket error:', error)
  })
  
  socketInstance.on('reconnect_attempt', (attemptNumber) => {
    console.log(`Reconnection attempt ${attemptNumber}`)
  })
  
  socketInstance.on('reconnect', (attemptNumber) => {
    console.log(`Reconnected after ${attemptNumber} attempts`)
  })
  
  socketInstance.on('reconnect_error', (error) => {
    console.error('Reconnection error:', error)
  })
  
  socketInstance.on('reconnect_failed', () => {
    console.error('Failed to reconnect')
  })
  
  return socketInstance
}

// Helper function to emit a message with debugging
export const emitMessage = (socket: Socket, event: string, data: any) => {
  if (!socket.connected) {
    console.warn('Socket not connected, attempting to reconnect')
    socket.connect()
  }
  
  console.log(`Emitting ${event}:`, data)
  socket.emit(event, data)
}

// Helper function to listen for messages with debugging
export const listenForMessages = (socket: Socket, event: string, callback: (data: any) => void) => {
  console.log(`Listening for ${event} events`)
  socket.on(event, (data) => {
    console.log(`Received ${event}:`, data)
    callback(data)
  })
} 