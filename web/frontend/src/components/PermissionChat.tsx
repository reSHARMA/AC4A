import { useState, useEffect } from 'react'
import { Box, Text, VStack, Spinner, Accordion, AccordionItem, AccordionButton, AccordionPanel, AccordionIcon } from '@chakra-ui/react'
import { FaFolder, FaFolderOpen, FaFile } from 'react-icons/fa'
import styles from './Chat.module.css'

interface TreeNode {
  label: string;
  value: string;
  children: TreeNode[];
}

const TreeView = ({ data, isRoot = false }: { data: TreeNode, isRoot?: boolean }) => {
  const [isOpen, setIsOpen] = useState(false);
  const hasChildren = data.children && data.children.length > 0;
  
  return (
    <Box ml={isRoot ? 0 : 2}>
      <Box 
        display="flex" 
        alignItems="center" 
        cursor={hasChildren ? "pointer" : "default"}
        py={1}
        onClick={() => hasChildren && setIsOpen(!isOpen)}
      >
        {hasChildren ? (
          isOpen ? <FaFolderOpen color="#F9A826" /> : <FaFolder color="#F9A826" />
        ) : (
          <FaFile color="#718096" />
        )}
        <Text ml={2} fontWeight={hasChildren ? "medium" : "normal"}>
          {data.label} {data.value !== '*' && data.value !== data.label && `(${data.value})`}
        </Text>
      </Box>
      
      {isOpen && hasChildren && (
        <Box ml={4} borderLeftWidth="1px" borderLeftColor="gray.200" pl={2}>
          {data.children.map((child, index) => (
            <TreeView key={index} data={child} />
          ))}
        </Box>
      )}
    </Box>
  );
};

const PermissionChat = () => {
  const [attributeTrees, setAttributeTrees] = useState<TreeNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Use the full URL if we're in production, otherwise use the relative path
    const apiUrl = import.meta.env.PROD 
      ? 'http://localhost:5000/get_attribute_trees' 
      : '/get_attribute_trees';
    
    console.log('Fetching from:', apiUrl);
    
    fetch(apiUrl)
      .then(response => {
        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);
        
        if (!response.ok) {
          return response.text().then(text => {
            console.error('Error response text:', text);
            throw new Error(`Failed to fetch attribute trees: ${response.status} ${response.statusText}`);
          });
        }
        
        return response.json();
      })
      .then(data => {
        console.log('Received data:', data);
        setAttributeTrees(data.attribute_trees || []);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching attribute trees:', err);
        setError(err.message);
        setLoading(false);
      });
  }, []);

  return (
    <div className={styles.chatContainer}>
      <Box className={styles.messagesContainer} overflow="auto">
        <Text fontSize="lg" fontWeight="bold" mb={4}>
          Permission Attribute Trees
        </Text>
        
        {loading && (
          <Box textAlign="center" py={4}>
            <Spinner size="md" />
            <Text mt={2}>Loading attribute trees...</Text>
          </Box>
        )}
        
        {error && (
          <Box bg="red.50" p={3} borderRadius="md" color="red.600">
            <Text>Error: {error}</Text>
            <Text fontSize="sm" mt={1}>
              Please refresh the page or contact support if the issue persists.
            </Text>
          </Box>
        )}
        
        {!loading && !error && attributeTrees.length === 0 && (
          <Box p={3} borderRadius="md" bg="gray.50">
            <Text>No attribute trees available yet.</Text>
          </Box>
        )}
        
        {!loading && !error && attributeTrees.length > 0 && (
          <VStack align="stretch" spacing={2} width="100%">
            {attributeTrees.map((tree, index) => (
              <Box key={index} p={2} borderRadius="md" bg="white" boxShadow="sm">
                <TreeView data={tree} isRoot={true} />
              </Box>
            ))}
          </VStack>
        )}
      </Box>
    </div>
  );
};

export default PermissionChat; 