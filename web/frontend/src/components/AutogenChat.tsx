import React, { useState, useEffect, useRef } from 'react'
import { Socket, io } from 'socket.io-client'
import styles from './Chat.module.css'
import { emitMessage } from '../utils/socketUtils'

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
  const [isLoading, setIsLoading] = useState(true)
  const socketRef = useRef<Socket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const lastMessageRef = useRef<string>('')

  useEffect(() => {
    // Use direct socket connection with minimal configuration
    const baseUrl = import.meta.env.PROD 
      ? 'http://localhost:5000' 
      : 'http://localhost:5000';
    
    console.log('Initializing socket connection to:', baseUrl);
    setIsLoading(true);
    
    socketRef.current = io(baseUrl, {
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 20000,
      autoConnect: true,
      transports: ['websocket', 'polling'],
      forceNew: false,
      path: '/socket.io/',
      withCredentials: true,
      extraHeaders: {
        'Access-Control-Allow-Origin': '*'
      }
    });
    
    // Set up connection status
    socketRef.current.on('connect', () => {
      console.log('Socket connected');
      setIsConnected(true);
      setIsLoading(false);
    });
    
    socketRef.current.on('disconnect', (reason) => {
      console.log('Socket disconnected:', reason);
      setIsConnected(false);
      setIsLoading(true);
    });
    
    socketRef.current.on('connect_error', (error) => {
      console.error('Socket connection error:', error);
      setIsConnected(false);
      setIsLoading(true);
    });
    
    // Listen for input requests from the agent
    socketRef.current.on('input_request', (data: { prompt: string, can_input: boolean, input_enabled: boolean }) => {
      console.log('Received input request:', data);
      setIsWaitingForInput(true);
      setInputPrompt(data.prompt);
      setIsLoading(false);
      
      // Add the prompt as a system message
      setMessages(prev => [...prev, { role: 'System', content: data.prompt }]);
      
      // Focus the input field
      if (inputRef.current) {
        inputRef.current.focus();
      }
    });
    
    // Listen for messages from the server
    socketRef.current.on('message', (data: Message) => {
      console.log('Received message:', data);
      setMessages(prev => [...prev, data]);
      setIsLoading(false);
    });

    // Listen for function calls from the agent
    socketRef.current.on('function_call', (data: { function_call: any }) => {
      console.log('Received function call:', data);
      setIsWaitingForInput(true);
      setInputPrompt(data.function_call.arguments || '');
      setIsLoading(false);
      
      // Add the function call as a system message
      setMessages(prev => [...prev, { 
        role: 'System', 
        content: `Function call: ${JSON.stringify(data.function_call)}` 
      }]);
      
      // Focus the input field
      if (inputRef.current) {
        inputRef.current.focus();
      }
    });

    return () => {
      if (socketRef.current) {
        console.log('Cleaning up socket connection');
        socketRef.current.disconnect();
      }
    };
  }, [setMessages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || !socketRef.current) return;

    const message: Message = {
      role: 'user',
      content: input
    };

    // If we're waiting for input (function call response), send it as a function response
    if (isWaitingForInput) {
      emitMessage(socketRef.current, 'function_response', {
        response: input
      });
    } else {
      // Otherwise send it as a regular message
      emitMessage(socketRef.current, 'user_message', message);
    }
    
    // Add it to the local state
    setMessages(prev => [...prev, message]);
    setInput('');
    setIsWaitingForInput(false);
    setIsLoading(true);
  };

  return (
    <div className={styles.chatContainer} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className={styles.messagesContainer} style={{ flex: 1, overflowY: 'auto', maxHeight: 'calc(100vh - 200px)' }}>
        {isLoading ? (
          <div className={styles.loadingContainer}>
            <div className={styles.loadingSpinner}></div>
            <div className={styles.loadingText}>
              {!isConnected ? 'Connecting to server...' : 'Waiting for response...'}
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`${styles.message} ${
                message.role === 'user' ? styles.userMessage : 
                message.role === 'System' ? styles.systemMessage : 
                styles.assistantMessage
              }`}
            >
              <div className={styles.messageHeader}>
                {message.role === 'user' ? 'You' : message.role}
              </div>
              <div>{message.content}</div>
            </div>
          ))
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
          disabled={!isConnected || isLoading}
        />
        <button
          className={styles.button}
          onClick={handleSend}
          disabled={!isConnected || isLoading}
        >
          Send
        </button>
      </div>
    </div>
  );
};

export default AutogenChat; 