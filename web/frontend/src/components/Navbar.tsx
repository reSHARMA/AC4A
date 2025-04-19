import { Box, Flex, Heading, Button, useColorMode } from '@chakra-ui/react'

const Navbar = () => {
  const { colorMode, toggleColorMode } = useColorMode()

  return (
    <Box as="nav" bg="white" boxShadow="sm" position="sticky" top={0} zIndex={10}>
      <Flex
        maxW="container.xl"
        mx="auto"
        px={4}
        py={4}
        align="center"
        justify="space-between"
      >
        <Heading size="lg" color="brand.600">
          Data Policy Lang
        </Heading>
        <Flex gap={4}>
          <Button
            variant="ghost"
            onClick={toggleColorMode}
            aria-label="Toggle color mode"
          >
            {colorMode === 'light' ? '🌙' : '☀️'}
          </Button>
          <Button colorScheme="brand" variant="solid">
            Connect
          </Button>
        </Flex>
      </Flex>
    </Box>
  )
}

export default Navbar 