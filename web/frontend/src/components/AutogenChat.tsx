import { useState, useEffect, useRef } from 'react'
import { Socket } from 'socket.io-client'
import styles from './Chat.module.css'
import { createSocketConnection, emitMessage, listenForMessages } from '../utils/socketUtils'
import ReactMarkdown from 'react-markdown'
import { Switch, FormControl, FormLabel, HStack, useColorModeValue } from '@chakra-ui/react'

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
  const [isVideoMode, setIsVideoMode] = useState(false)
  const [videoMessages, setVideoMessages] = useState<Message[]>([])
  const socketRef = useRef<Socket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [isAssistantTyping, setIsAssistantTyping] = useState(false)
  const [isVncLoading, setIsVncLoading] = useState(true)

  // Function to add message to the appropriate queue
  const addMessage = (message: Message) => {
    if (isVideoMode) {
      setVideoMessages(prev => [...prev, message])
    } else {
      setMessages(prev => [...prev, message])
    }
  }

  useEffect(() => {
    // Create socket connection with debugging
    const port = import.meta.env.VITE_PORT || 5000;
    socketRef.current = createSocketConnection(`http://localhost:${port}`)
    
    // Set up connection status
    socketRef.current.on('connect', () => {
      setIsConnected(true)
    })
    
    socketRef.current.on('disconnect', () => {
      setIsConnected(false)
    })
    
    // Listen for input requests from the agent
    socketRef.current.on('input_request', (data: { prompt: string, isVideoMode: boolean }) => {
      console.log('Received input request:', data)
      // Only handle input requests for the current mode
      if (data.isVideoMode === isVideoMode) {
        setIsWaitingForInput(true)
        setInputPrompt(data.prompt)
        setIsAssistantTyping(false)
        
        // Add the prompt as a system message to the current mode's queue
        const systemMessage = { role: 'System', content: data.prompt }
        addMessage(systemMessage)
        
        // Focus the input field
        if (inputRef.current) {
          inputRef.current.focus()
        }
      }
    })
    
    // Listen for system_ready event from backend
    socketRef.current.on('system_ready', () => {
      const systemMessage = { role: 'System', content: 'System is ready' }
      addMessage(systemMessage)
    })
    
    // Listen for different message types
    listenForMessages(socketRef.current, 'agent_message', (message: Message & { isVideoMode?: boolean }) => {
      // Only handle messages for the current mode
      if (message.isVideoMode === isVideoMode) {
        addMessage(message)
        // Check if message starts with "Chat Session Ended"
        if (message.content.startsWith('Chat Session Ended')) {
          setIsAssistantTyping(false)
        }
      }
    })
    
    listenForMessages(socketRef.current, 'user_message', (message: Message & { isVideoMode?: boolean }) => {
      // Only handle messages for the current mode
      if (message.isVideoMode === isVideoMode) {
        addMessage(message)
      }
    })
    
    listenForMessages(socketRef.current, 'system_message', (message: Message & { isVideoMode?: boolean }) => {
      // Only handle messages for the current mode
      if (message.isVideoMode === isVideoMode) {
        addMessage(message)
        // Also check system messages for session end
        if (message.content.startsWith('Chat Session Ended')) {
          setIsAssistantTyping(false)
        }
      }
    })
    
    // Fallback for any message
    listenForMessages(socketRef.current, 'message', (message: Message & { isVideoMode?: boolean }) => {
      // Only handle messages for the current mode
      if (message.isVideoMode === isVideoMode) {
        addMessage(message)
        // Check all messages for session end
        if (message.content.startsWith('Chat Session Ended')) {
          setIsAssistantTyping(false)
        }
      }
    })

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect()
      }
    }
  }, [setMessages, isVideoMode]) // Added isVideoMode to dependencies

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, videoMessages]) // Added videoMessages to dependencies

  const handleSend = () => {
    if (!input.trim() || !socketRef.current) return

    const message: Message = {
      role: 'user',
      content: input
    }

    // Emit the message using our utility function with mode information
    emitMessage(socketRef.current, 'user_message', { ...message, isVideoMode })

    // Add it to the appropriate queue
    addMessage(message)
    setInput('')
    setIsWaitingForInput(false)
    setIsAssistantTyping(true)
  }

  // Function to render messages from the current mode's queue
  const renderMessages = (messageList: Message[]) => {
    if (messageList.length === 0) {
      return (
        <div className={styles.message}>
          <div className={styles.messageHeader}>System</div>
          <div>System is initializing...</div>
        </div>
      )
    }

    return messageList.map((message, index) => (
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
  }

  return (
    <div className={styles.chatContainer} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1rem' }}>
        <FormControl display="flex" alignItems="center" width="auto">
          <HStack spacing={2}>
            <FormLabel htmlFor="video-toggle" mb="0" fontSize="sm" color={useColorModeValue('gray.600', 'gray.300')}>
              {isVideoMode ? 'Browser Mode' : 'Chat Mode'}
            </FormLabel>
            <Switch
              id="video-toggle"
              isChecked={isVideoMode}
              onChange={() => setIsVideoMode(!isVideoMode)}
              colorScheme="blue"
              size="md"
            />
          </HStack>
        </FormControl>
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%' }}>
        {isVideoMode ? (
          <div style={{ flex: 1, background: 'black', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
            {isVncLoading && (
              <div style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                zIndex: 1,
                color: 'white',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '1rem'
              }}>
                <div className={styles.typingDot}></div>
                <div>Connecting to browser...</div>
              </div>
            )}
            <iframe
              src="http://localhost:6080/vnc.html?autoconnect=true&host=localhost&port=6080"
              style={{
                width: '100%',
                height: '100%',
                border: 'none',
                backgroundColor: 'black',
                opacity: isVncLoading ? 0 : 1,
                transition: 'opacity 0.3s ease-in-out'
              }}
              title="VNC Browser View"
              onLoad={() => setIsVncLoading(false)}
            />
          </div>
        ) : (
          <div className={styles.messagesContainer} style={{ flex: 1, overflowY: 'auto', maxHeight: 'calc(100vh - 200px)' }}>
            {renderMessages(messages)}
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
        )}
        {/* Input area always visible at the bottom */}
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
    </div>
  )
}

export default AutogenChat 
