import { useState, useEffect } from 'react'
import Split from 'react-split'
import { Box, Container, Flex, useToast } from '@chakra-ui/react'
import PermissionChat from './components/PermissionChat'
import AutogenChat from './components/AutogenChat'
import Navbar from './components/Navbar'

function App() {
  const [messages, setMessages] = useState<Array<{role: string, content: string}>>([])
  const [isConnected, setIsConnected] = useState(false)
  const toast = useToast()

  // Reset messages when component mounts (page load/refresh)
  useEffect(() => {
    setMessages([])
  }, [])

  useEffect(() => {
    console.log('WebSocket connection status:', isConnected ? 'Connected' : 'Disconnected')
    if (!isConnected) {
      toast({
        title: 'Connection Status',
        description: 'WebSocket is disconnected',
        status: 'warning',
        duration: 3000,
        isClosable: true,
      })
    }
  }, [isConnected, toast])

  return (
    <Box minH="100vh" bg="gray.50">
      <Navbar />
      <Container 
        maxW="container.xl" 
        py={8}
        px={{ base: 2, md: 4 }}
      >
        <Box
          bg="white"
          borderRadius="2xl"
          boxShadow="xl"
          p={{ base: 4, md: 8 }}
          transition="all 0.2s"
          _hover={{ boxShadow: '2xl' }}
          minH="600px"
        >
          <Split
            sizes={[54, 46]}
            minSize={300}
            expandToMin={false}
            gutterSize={10}
            gutterAlign="center"
            snapOffset={30}
            dragInterval={1}
            direction="horizontal"
            cursor="col-resize"
            style={{ display: 'flex', height: '100%' }}
          >
            <Box p={4} borderRight="1px" borderColor="gray.200">
              <PermissionChat />
            </Box>
            <Box p={4}>
              <AutogenChat messages={messages} setMessages={setMessages} />
            </Box>
          </Split>
        </Box>
      </Container>
    </Box>
  )
}

export default App
