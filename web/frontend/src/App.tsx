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
      <Container maxW="container.xl" py={8}>
        <Flex direction="column" gap={6}>
          <Box
            bg="white"
            borderRadius="lg"
            boxShadow="md"
            overflow="hidden"
            minH="600px"
          >
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
        </Flex>
      </Container>
    </Box>
  )
}

export default App
