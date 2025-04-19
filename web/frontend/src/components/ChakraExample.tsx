import React from 'react';
import { Box, Button, Heading, Text, VStack } from '@chakra-ui/react';

const ChakraExample = () => {
  return (
    <Box p={8} bg="gray.100" borderRadius="lg" boxShadow="md">
      <VStack gap={4} align="start">
        <Heading size="lg" color="gray.800">
          Chakra UI Example
        </Heading>
        <Text color="gray.800">
          This is a simple example of using Chakra UI components.
        </Text>
        <Button colorScheme="blue">
          Click Me
        </Button>
      </VStack>
    </Box>
  );
};

export default ChakraExample; 