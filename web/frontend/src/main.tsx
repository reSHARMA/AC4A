import React from 'react'
import ReactDOM from 'react-dom/client'
import { ChakraProvider } from '@chakra-ui/react'
import { Provider } from './components/ui/provider'
import App from './App'
import theme from './theme'
import './index.css'

// Add a global error handler for WebSocket errors
window.addEventListener('error', (event) => {
  console.error('Global error:', event.error)
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ChakraProvider theme={theme}>
      <Provider>
        <App />
      </Provider>
    </ChakraProvider>
  </React.StrictMode>,
)
