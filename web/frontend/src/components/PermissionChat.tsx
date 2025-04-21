import { useState, useEffect } from 'react'
import { Box, Text, VStack, Spinner, Select, HStack, Badge } from '@chakra-ui/react'
import { FaFolder, FaFolderOpen, FaFile } from 'react-icons/fa'
import styles from './Chat.module.css'

interface TreeNode {
  label: string;
  value: string;
  children: TreeNode[];
  access?: string;
  position?: string;
}

const TreeView = ({ data, isRoot = false, onAccessChange, onPositionChange }: { 
  data: TreeNode, 
  isRoot?: boolean,
  onAccessChange?: (node: TreeNode, value: string) => void,
  onPositionChange?: (node: TreeNode, value: string) => void
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const hasChildren = data.children && data.children.length > 0;
  
  const handleAccessChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    if (onAccessChange) {
      onAccessChange(data, e.target.value);
    }
  };
  
  const handlePositionChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    if (onPositionChange) {
      onPositionChange(data, e.target.value);
    }
  };
  
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
        
        <HStack ml="auto" spacing={2}>
          <Select 
            size="xs" 
            width="80px" 
            value={data.access || ""} 
            onChange={handleAccessChange}
            onClick={(e) => e.stopPropagation()}
            placeholder="Access"
          >
            <option value="read">Read</option>
            <option value="write">Write</option>
          </Select>
          
          <Select 
            size="xs" 
            width="90px" 
            value={data.position || ""} 
            onChange={handlePositionChange}
            onClick={(e) => e.stopPropagation()}
            placeholder="Position"
          >
            <option value="previous">Previous</option>
            <option value="current">Current</option>
            <option value="next">Next</option>
          </Select>
        </HStack>
      </Box>
      
      {isOpen && hasChildren && (
        <Box ml={4} borderLeftWidth="1px" borderLeftColor="gray.200" pl={2}>
          {data.children.map((child, index) => (
            <TreeView 
              key={index} 
              data={child} 
              onAccessChange={onAccessChange}
              onPositionChange={onPositionChange}
            />
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

  const handleAccessChange = (node: TreeNode, value: string) => {
    // Create a deep copy of the trees to avoid mutating state directly
    const updatedTrees = JSON.parse(JSON.stringify(attributeTrees));
    
    // Function to update the node in the tree
    const updateNode = (trees: TreeNode[]): boolean => {
      for (let i = 0; i < trees.length; i++) {
        if (trees[i] === node) {
          trees[i].access = value;
          return true;
        }
        
        if (trees[i].children && trees[i].children.length > 0) {
          if (updateNode(trees[i].children)) {
            return true;
          }
        }
      }
      return false;
    };
    
    updateNode(updatedTrees);
    setAttributeTrees(updatedTrees);
    
    // Here you would typically send the updated trees to the backend
    console.log('Access updated:', node.label, value);
  };
  
  const handlePositionChange = (node: TreeNode, value: string) => {
    // Create a deep copy of the trees to avoid mutating state directly
    const updatedTrees = JSON.parse(JSON.stringify(attributeTrees));
    
    // Function to update the node in the tree
    const updateNode = (trees: TreeNode[]): boolean => {
      for (let i = 0; i < trees.length; i++) {
        if (trees[i] === node) {
          trees[i].position = value;
          return true;
        }
        
        if (trees[i].children && trees[i].children.length > 0) {
          if (updateNode(trees[i].children)) {
            return true;
          }
        }
      }
      return false;
    };
    
    updateNode(updatedTrees);
    setAttributeTrees(updatedTrees);
    
    // Here you would typically send the updated trees to the backend
    console.log('Position updated:', node.label, value);
  };

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
                <TreeView 
                  data={tree} 
                  isRoot={true} 
                  onAccessChange={handleAccessChange}
                  onPositionChange={handlePositionChange}
                />
              </Box>
            ))}
          </VStack>
        )}
      </Box>
    </div>
  );
};

export default PermissionChat; 