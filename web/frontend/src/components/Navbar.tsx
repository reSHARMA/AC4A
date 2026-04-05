import { Box, Container, Flex, Heading, Text, Button, HStack } from '@chakra-ui/react'

interface NavbarProps {
  activeView?: 'main' | 'testing'
  onViewChange?: (view: 'main' | 'testing') => void
}

const Navbar: React.FC<NavbarProps> = ({ activeView = 'main', onViewChange }) => {
  return (
    <Box 
      as="nav" 
      bg="white" 
      boxShadow="sm" 
      position="sticky" 
      top={0} 
      zIndex={10}
      borderBottom="1px"
      borderColor="gray.100"
      backdropFilter="blur(10px)"
      backgroundColor="rgba(255, 255, 255, 0.9)"
    >
      <Container maxW="container.xl" py={4}>
        <Flex align="center" justify="space-between">
          <Box>
            <Heading 
              size="lg" 
              color="brand.800"
              letterSpacing="tight"
              fontWeight="extrabold"
              cursor="pointer"
              onClick={() => onViewChange?.('main')}
              position="relative"
              _after={{
                content: '""',
                position: 'absolute',
                bottom: '-2px',
                left: '0',
                width: '100%',
                height: '2px',
                bg: 'brand.600',
                transform: 'scaleX(0)',
                transformOrigin: 'left',
                transition: 'transform 0.3s ease-in-out',
                _groupHover: {
                  transform: 'scaleX(1)',
                },
              }}
              _hover={{
                color: 'brand.700',
              }}
            >
              AC4A: <Text as="span" fontWeight="medium" color="brand.600">Access Control for Agents</Text>
            </Heading>
          </Box>
          <HStack spacing={2}>
            <Button
              size="sm"
              variant={activeView === 'main' ? 'solid' : 'ghost'}
              colorScheme="blue"
              onClick={() => onViewChange?.('main')}
            >
              Dashboard
            </Button>
            <Button
              size="sm"
              variant={activeView === 'testing' ? 'solid' : 'ghost'}
              colorScheme="blue"
              onClick={() => onViewChange?.('testing')}
            >
              Testing
            </Button>
          </HStack>
        </Flex>
      </Container>
    </Box>
  )
}

export default Navbar 