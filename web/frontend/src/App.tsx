import { useState, useEffect } from 'react'
import Split from 'react-split'
import PermissionChat from './components/PermissionChat'
import AutogenChat from './components/AutogenChat'
import ChakraExample from './components/ChakraExample'
import styles from './App.module.css'

function App() {
  const [messages, setMessages] = useState<Array<{role: string, content: string}>>([])
  const [isConnected, setIsConnected] = useState(false)

  // Log connection status
  useEffect(() => {
    console.log('WebSocket connection status:', isConnected ? 'Connected' : 'Disconnected')
  }, [isConnected])

  return (
    <div className={styles.container}>
      <div className={styles.chatContainer}>
        <Split
          sizes={[35, 65]}
          minSize={300}
          expandToMin={false}
          gutterSize={10}
          gutterAlign="center"
          snapOffset={30}
          dragInterval={1}
          direction="horizontal"
          cursor="col-resize"
          className={styles.splitContainer}
        >
          <div className={styles.chatBox}>
            <PermissionChat />
          </div>
          <div className={styles.chatBox}>
            <AutogenChat messages={messages} setMessages={setMessages} />
          </div>
        </Split>
      </div>
      <div style={{ margin: '20px', maxWidth: '600px' }}>
        <ChakraExample />
      </div>
    </div>
  )
}

export default App
