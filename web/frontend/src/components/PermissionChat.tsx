import { useState } from 'react'
import styles from './Chat.module.css'

const PermissionChat = () => {
  const [input, setInput] = useState('')

  const handleSend = () => {
    if (!input.trim()) return
    
    // This is a dummy function for now
    console.log('Permission chat message:', input)
    setInput('')
  }

  return (
    <div className={styles.chatContainer}>
      <div className={styles.messagesContainer}>
        <div className={styles.message}>
          <div className={styles.messageHeader}>System</div>
          <div>Permission Chat Interface</div>
        </div>
        <div className={styles.message}>
          <div className={styles.messageHeader}>System</div>
          <div>(Dummy Interface - Coming Soon)</div>
        </div>
      </div>
      
      <div className={styles.inputContainer}>
        <input
          className={styles.input}
          placeholder="Type your message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
        />
        <button
          className={styles.button}
          onClick={handleSend}
        >
          Send
        </button>
      </div>
    </div>
  )
}

export default PermissionChat 