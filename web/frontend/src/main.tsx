import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// Add a global error handler for WebSocket errors
window.addEventListener('error', (event) => {
  console.error('Global error:', event.error)
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
