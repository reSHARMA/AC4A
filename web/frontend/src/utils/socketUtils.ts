import { io, Socket } from 'socket.io-client'

// Create a socket connection with debugging
export const createSocketConnection = (url: string): Socket => {
  console.log(`Connecting to WebSocket server at ${url}`)
  
  const socket = io(url, {
    transports: ['websocket'],
    upgrade: false,
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
    timeout: 20000,
  })
  
  // Add event listeners for debugging
  socket.on('connect', () => {
    console.log('Socket connected')
  })
  
  socket.on('disconnect', (reason) => {
    console.log(`Socket disconnected: ${reason}`)
  })
  
  socket.on('connect_error', (error) => {
    console.error('Socket connection error:', error)
  })
  
  socket.on('error', (error) => {
    console.error('Socket error:', error)
  })
  
  return socket
}

// Helper function to emit a message with debugging
export const emitMessage = (socket: Socket, event: string, data: any) => {
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