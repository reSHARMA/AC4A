import { Box, Flex, Heading } from '@chakra-ui/react'

const Navbar = () => {
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
          AC4A: Access Control for Agents
        </Heading>
      </Flex>
    </Box>
  )
}

export default Navbar 