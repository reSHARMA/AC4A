import { useState, useEffect, useRef } from 'react'
import { Socket } from 'socket.io-client'
import styles from './Chat.module.css'
import { createSocketConnection, emitMessage, listenForMessages } from '../utils/socketUtils'
import ReactMarkdown from 'react-markdown'

interface Message {
  role: string
  content: string
}

interface AutogenChatProps {
  messages: Message[]
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>
}

const AutogenChat = ({ messages, setMessages }: AutogenChatProps) => {
  const [input, setInput] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [isWaitingForInput, setIsWaitingForInput] = useState(false)
  const [inputPrompt, setInputPrompt] = useState('')
  const socketRef = useRef<Socket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [isAssistantTyping, setIsAssistantTyping] = useState(false)

  useEffect(() => {
    // Create socket connection with debugging
    const port = import.meta.env.PORT || 5000;
    socketRef.current = createSocketConnection(`http://localhost:${port}`)
    
    // Set up connection status
    socketRef.current.on('connect', () => {
      setIsConnected(true)
    })
    
    socketRef.current.on('disconnect', () => {
      setIsConnected(false)
    })
    
    // Listen for input requests from the agent
    socketRef.current.on('input_request', (data: { prompt: string }) => {
      console.log('Received input request:', data)
      setIsWaitingForInput(true)
      setInputPrompt(data.prompt)
      setIsAssistantTyping(false)
      
      // Add the prompt as a system message
      setMessages(prev => [...prev, { role: 'System', content: data.prompt }])
      
      // Focus the input field
      if (inputRef.current) {
        inputRef.current.focus()
      }
    })
    
    // Listen for system_ready event from backend
    socketRef.current.on('system_ready', () => {
      setMessages(prev => [...prev, { role: 'System', content: 'System is ready' }])
    })
    
    // Listen for different message types
    listenForMessages(socketRef.current, 'agent_message', (message: Message) => {
      setMessages(prev => [...prev, message])
      setIsAssistantTyping(false)
    })
    
    listenForMessages(socketRef.current, 'user_message', (message: Message) => {
      setMessages(prev => [...prev, message])
    })
    
    listenForMessages(socketRef.current, 'system_message', (message: Message) => {
      setMessages(prev => [...prev, message])
    })
    
    // Fallback for any message
    listenForMessages(socketRef.current, 'message', (message: Message) => {
      setMessages(prev => [...prev, message])
    })

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect()
      }
    }
  }, [setMessages])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    if (!input.trim() || !socketRef.current) return

    const message: Message = {
      role: 'user',
      content: input
    }

    // Emit the message using our utility function
    emitMessage(socketRef.current, 'user_message', message)
    
    // Also add it to the local state
    setMessages(prev => [...prev, message])
    setInput('')
    setIsWaitingForInput(false)
    setIsAssistantTyping(true)
  }

  return (
    <div className={styles.chatContainer} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className={styles.messagesContainer} style={{ flex: 1, overflowY: 'auto', maxHeight: 'calc(100vh - 200px)' }}>
        {messages.length === 0 ? (
          <div className={styles.message}>
            <div className={styles.messageHeader}>System</div>
            <div>System is initializing...</div>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`${styles.message} ${
                message.role === 'user' ? styles.userMessage : styles.assistantMessage
              }`}
            >
              <div className={styles.messageHeader}>
                {message.role === 'user' ? 'You' : 'Assistant'}
              </div>
              {message.role === 'user' ? (
                <div>{message.content}</div>
              ) : (
                <ReactMarkdown>{message.content}</ReactMarkdown>
              )}
            </div>
          ))
        )}
        {isAssistantTyping && (
          <div className={styles.typingIndicator}>
            Assistant is typing
            <span className={styles.typingDot}></span>
            <span className={styles.typingDot}></span>
            <span className={styles.typingDot}></span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <div className={styles.inputContainer} style={{ position: 'sticky', bottom: 0, background: 'white', padding: '1rem 0' }}>
        {isWaitingForInput && (
          <div className={styles.inputPrompt}>
            {inputPrompt}
          </div>
        )}
        <input
          ref={inputRef}
          className={styles.input}
          placeholder={isWaitingForInput ? "Type your response..." : "Type your message..."}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          disabled={!isConnected}
        />
        <button
          className={styles.button}
          onClick={handleSend}
          disabled={!isConnected}
        >
          Send
        </button>
      </div>
    </div>
  )
}

export default AutogenChat 
