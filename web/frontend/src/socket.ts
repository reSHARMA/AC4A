import { io } from 'socket.io-client';

const port = import.meta.env.VITE_PORT || '5002';
export const socket = io(`http://localhost:${port}/`, {
  transports: ['websocket'],
  upgrade: false,
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
  timeout: 20000
}); 