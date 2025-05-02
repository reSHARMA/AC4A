import { io } from 'socket.io-client';

const port = import.meta.env.VITE_PORT || '5000';
export const socket = io(`http://localhost:${port}`, {
  autoConnect: true,
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
  path: '/socket.io',
  transports: ['websocket'],
  forceNew: true
}); 