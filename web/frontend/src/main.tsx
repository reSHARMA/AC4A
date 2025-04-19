import React from 'react'
import ReactDOM from 'react-dom/client'
import { ChakraProvider } from '@chakra-ui/react'
import App from './App'
import './index.css'

// Add a global error handler for WebSocket errors
window.addEventListener('error', (event) => {
  console.error('Global error:', event.error)
})

// Create a custom provider to work around type issues
const AppProvider = ({ children }: { children: React.ReactNode }) => {
  // @ts-ignore - Ignoring type issues with ChakraProvider
  return <ChakraProvider>{children}</ChakraProvider>;
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AppProvider>
      <App />
    </AppProvider>
  </React.StrictMode>,
)
