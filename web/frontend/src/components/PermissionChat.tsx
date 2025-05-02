/** @jsxImportSource @emotion/react */
import React, { useState, useEffect, useRef, useMemo } from 'react'
import { Box, Text, VStack, Spinner, Select, HStack, Badge, Button, Switch, Input, IconButton } from '@chakra-ui/react'
import { MdAccountTree, MdSubdirectoryArrowRight, MdLabel, MdTextFields, MdViewList } from 'react-icons/md'
import { FaTrash } from 'react-icons/fa'
import styles from './PermissionChat.module.css'
import { io, Socket } from 'socket.io-client'
import { JSX } from 'react/jsx-runtime'
import PermissionModeSelector from './ui/PermissionModeSelector'
import LogsView from './LogsView'

interface TreeNode {
  label: string;
  value: string;
  access: string;
  position: string;
  positionValue?: number;
  children: TreeNode[];
}

interface Policy {
  granular_data: string;
  data_access: string;
  position: string;
  positionValue?: number;
}

interface TreeViewProps {
  data: TreeNode;
  isRoot: boolean;
  viewMode: ViewMode;
  onAccessChange?: (node: TreeNode, newAccess: string) => void;
  onPositionChange?: (node: TreeNode, newPosition: string, newPositionValue?: number) => void;
  onValueChange?: (node: TreeNode, newValue: string) => void;
  onDelete?: (node: TreeNode) => void;
  highlightedPolicy?: string | null;
}

interface Message {
  role: string;
  content: string;
}

type ViewMode = 'permitted' | 'edit' | 'all' | 'logs';
type DisplayMode = 'tree' | 'text';

const TreeView: React.FC<TreeViewProps> = ({ 
  data, 
  isRoot = false,
  viewMode,
  onAccessChange, 
  onPositionChange, 
  onValueChange,
  onDelete,
  highlightedPolicy = null
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isEditingValue, setIsEditingValue] = useState(false);
  const [editedValue, setEditedValue] = useState(data.value);
  const [isEditingPositionValue, setIsEditingPositionValue] = useState(false);
  const [editedPositionValue, setEditedPositionValue] = useState(data.positionValue || 1);
  const hasChildren = data.children && data.children.length > 0;

  // Check if this node should be highlighted
  const isHighlighted = useMemo(() => {
    if (!data.access || !data.position) return false;
    const policyKey = `${data.label}(${data.value || ''})-${data.access}-${data.position}${data.position !== "Current" && !data.position.includes('(') ? `::${data.positionValue || 1}` : ''}`;
    console.log('Checking highlight for node:', {
      nodeLabel: data.label,
      nodeValue: data.value,
      nodeAccess: data.access,
      nodePosition: data.position,
      constructedKey: policyKey,
      highlightedPolicy,
      isMatch: highlightedPolicy === policyKey
    });
    return highlightedPolicy === policyKey;
  }, [data, highlightedPolicy]);

  const handleAccessChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    if (onAccessChange) {
      onAccessChange(data, e.target.value);
    }
  };

  const handlePositionChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    if (onPositionChange) {
      const newPosition = e.target.value;
      if (newPosition === "Current") {
        onPositionChange(data, newPosition, 0);
      } else {
        onPositionChange(data, newPosition, data.positionValue || 1);
      }
    }
  };

  const handlePositionValueChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value);
    if (!isNaN(value) && value >= 0) {
      setEditedPositionValue(value);
    }
  };

  const handlePositionValueSubmit = () => {
    if (onPositionChange && data.position !== "Current") {
      onPositionChange(data, data.position, editedPositionValue);
    }
    setIsEditingPositionValue(false);
  };

  const handlePositionValueKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handlePositionValueSubmit();
    } else if (e.key === 'Escape') {
      setIsEditingPositionValue(false);
      setEditedPositionValue(data.positionValue || 1);
    }
  };

  const handleValueClick = () => {
    if (onValueChange) {
      setIsEditingValue(true);
    }
  };

  const handleValueSubmit = () => {
    if (onValueChange && editedValue !== data.value) {
      onValueChange(data, editedValue);
    }
    setIsEditingValue(false);
  };

  const handleValueKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleValueSubmit();
    } else if (e.key === 'Escape') {
      setIsEditingValue(false);
      setEditedValue(data.value);
    }
  };

  // Function to handle delete button click
  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent tree node expansion
    if (onDelete) {
      onDelete(data);
    }
  };

  // Function to get value display
  const getValueDisplay = () => {
    if (data.value === '') return "DEFAULT";
    if (data.value === '*') return "All Values";
    return data.value;
  };

  // Get the badge text for the value
  const getValueBadgeText = () => {
    if (data.value === '') return "DEFAULT";
    if (data.value === '*') return "All Values";
    return data.value;
  };

  return (
    <Box 
      className={`${styles.treeNode} ${isHighlighted ? styles.newPermission : ''}`}
      ml={isRoot ? 0 : 2} 
      width="100%"
      borderRadius="md"
      bg="transparent"
      boxShadow="none"
      minH="auto"
      _hover={{
        bg: isHighlighted ? 'yellow.100' : 'gray.50'
      }}
    >
      <Box 
        display="flex" 
        alignItems="center" 
        cursor={hasChildren ? "pointer" : "default"}
        py={1}
        onClick={() => hasChildren && setIsOpen(!isOpen)}
        width="100%"
      >
        {hasChildren ? (
          isOpen ? <MdAccountTree color="#F9A826" size={20} /> : <MdAccountTree color="#F9A826" size={20} />
        ) : (
          <MdLabel color="#718096" size={20} />
        )}
        <Text ml={2} fontWeight={hasChildren ? "medium" : "normal"} flex={1}>
          {data.label}
        </Text>
        
        <HStack spacing={2} justify="flex-end" minW="300px">
          {/* Value badge/input */}
          {onValueChange ? (
            isEditingValue ? (
              <Input
                size="xs"
                width="100px"
                value={editedValue}
                onChange={(e) => setEditedValue(e.target.value)}
                onKeyDown={handleValueKeyPress}
                onBlur={handleValueSubmit}
                autoFocus
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <Badge 
                colorScheme="green" 
                cursor="pointer"
                onClick={(e) => {
                  e.stopPropagation();
                  handleValueClick();
                }}
              >
                {getValueBadgeText()}
              </Badge>
            )
          ) : (
            <Badge colorScheme="green">
              {getValueBadgeText()}
            </Badge>
          )}

          {/* Access badge/select */}
          {onAccessChange ? (
            <Select 
              size="xs" 
              width="80px" 
              value={data.access || ""} 
              onChange={handleAccessChange}
              onClick={(e) => e.stopPropagation()}
              placeholder="Access"
            >
              <option value="Read">Read</option>
              <option value="Write">Write</option>
            </Select>
          ) : (
            <Badge colorScheme="blue">
              {data.access ? data.access.toUpperCase() : "Access"}
            </Badge>
          )}
              
          {/* Position badge/select and value input */}
          {onPositionChange ? (
            <HStack spacing={1}>
              <Select 
                size="xs" 
                width="90px" 
                value={data.position || ""} 
                onChange={handlePositionChange}
                onClick={(e) => e.stopPropagation()}
                placeholder="Position"
              >
                <option value="Previous">Previous</option>
                <option value="Current">Current</option>
                <option value="Next">Next</option>
              </Select>
              {data.position && data.position !== "Current" && !data.position.includes('(') && (
                isEditingPositionValue ? (
                  <Input
                    size="xs"
                    width="50px"
                    type="number"
                    min="0"
                    value={editedPositionValue}
                    onChange={handlePositionValueChange}
                    onKeyDown={handlePositionValueKeyPress}
                    onBlur={handlePositionValueSubmit}
                    autoFocus
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <Badge 
                    colorScheme="purple" 
                    cursor="pointer"
                    onClick={(e) => {
                      e.stopPropagation();
                      setIsEditingPositionValue(true);
                    }}
                  >
                    {data.positionValue || 1}
                  </Badge>
                )
              )}
            </HStack>
          ) : (
            <Badge colorScheme="purple">
              {data.position ? `${data.position !== "Current" ? data.position : ""}${data.position !== "Current" && !data.position.includes('(') && (data.positionValue || data.positionValue === 0) ? `::${data.positionValue}` : ''}` : "Position"}
            </Badge>
          )}

          {/* Delete button - only show in all permission view */}
          {isRoot && onDelete && viewMode === 'permitted' && (
            <IconButton
              size="xs"
              variant="ghost"
              colorScheme="red"
              aria-label="Delete policy"
              icon={<FaTrash />}
              onClick={handleDelete}
              _hover={{
                bg: 'red.100'
              }}
              color="red.500"
            />
          )}
        </HStack>
      </Box>
      
      {isOpen && hasChildren && (
        <Box ml={4} borderLeftWidth="1px" borderLeftColor="gray.200" pl={2}>
          {data.children.map((child, index) => (
            <Box key={index} display="flex" alignItems="center">
              <MdSubdirectoryArrowRight color="#718096" size={16} />
              <TreeView
                data={child}
                isRoot={false}
                viewMode={viewMode}
                onAccessChange={onAccessChange}
                onPositionChange={onPositionChange}
                onValueChange={onValueChange}
                onDelete={onDelete}
                highlightedPolicy={highlightedPolicy}
              />
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
};

const PermissionChat: React.FC = (): JSX.Element => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [attributeTrees, setAttributeTrees] = useState<TreeNode[]>([]);
  const [editViewTrees, setEditViewTrees] = useState<TreeNode[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('permitted');
  const [displayMode, setDisplayMode] = useState<DisplayMode>('tree');
  const [permissionTexts, setPermissionTexts] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const [socket, setSocket] = useState<Socket | null>(null);
  const [nodeMap, setNodeMap] = useState<Map<string, TreeNode>>(new Map());
  const [shouldApplyPolicies, setShouldApplyPolicies] = useState(false);
  const [policyText, setPolicyText] = useState('');
  const [highlightedPolicy, setHighlightedPolicy] = useState<string | null>(null);

  // Function to reset trees for edit view
  const resetEditViewTrees = (trees: TreeNode[]): TreeNode[] => {
    return trees.map(tree => ({
      ...tree,
      value: '',
      access: '',
      position: '',
      children: tree.children ? resetEditViewTrees(tree.children) : []
    }));
  };

  // Handle view mode changes
  const handleViewModeChange = (newMode: ViewMode) => {
    if (newMode === 'edit') {
      // Create a fresh copy of the current trees for edit view
      const freshEditTrees = resetEditViewTrees(JSON.parse(JSON.stringify(attributeTrees)));
      setEditViewTrees(freshEditTrees);
    }
    setViewMode(newMode);
  };

  // Initialize socket connection
  useEffect(() => {
    // Use the full URL if we're in production, otherwise use the relative path
    const port = import.meta.env.VITE_PORT || 5000;
    const baseUrl = import.meta.env.PROD 
      ? `http://localhost:${port}` 
      : `http://localhost:${port}`;
    
    console.log('Initializing socket connection to:', baseUrl);
    const newSocket = io(baseUrl, {
      transports: ['websocket'],
      upgrade: false,
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      timeout: 20000
    });
    
    // Set up event listeners
    newSocket.on('connect', () => {
      console.log('Socket connected');
    });
    
    newSocket.on('disconnect', () => {
      console.log('Socket disconnected');
    });
    
    newSocket.on('policy_update', (data) => {
      console.log('Received policy update:', data);
      setAttributeTrees(data.attribute_trees || []);
      setPolicies(data.policies || []);
      setIsLoading(false);
    });
    
    newSocket.on('highlight_policy', (policyKey: string) => {
      console.log('Received highlight_policy event:', {
        policyKey,
        currentHighlightedPolicy: highlightedPolicy
      });
      setHighlightedPolicy(policyKey);
      
      // Clear the highlight after animation completes (3 seconds)
      setTimeout(() => {
        console.log('Clearing policy highlight');
        setHighlightedPolicy(null);
      }, 3000);
    });
    
    setSocket(newSocket);
    
    // Clean up on unmount
    return () => {
      console.log('Cleaning up socket connection');
      newSocket.disconnect();
    };
  }, []);

  // Create node map when attribute trees are loaded
  useEffect(() => {
    if (attributeTrees.length > 0) {
      console.log('Initializing node map with attribute trees');
      console.log('Current node map size before initialization:', nodeMap.size);
      
      // Create a new map instead of modifying the existing one
      const newNodeMap = new Map<string, TreeNode>();
      
      const addNodesToMap = (node: TreeNode) => {
        const nodeKey = createNodeKey(node.label, node.access || '', node.position || '', node.positionValue || 1);
        console.log('Adding node to map:', {
          nodeLabel: node.label,
          nodeAccess: node.access,
          nodePosition: node.position,
          nodeKey
        });
        
        // Map the composite key to the full node data
        newNodeMap.set(nodeKey, {
          ...node,
          label: node.label, // Use the base label without the value
          value: node.value || '', // Preserve existing value or use parsed value
          access: node.access || '', // Ensure access is preserved
          position: node.position || '' // Ensure position is preserved
        });
        
        // Process children
        if (node.children && node.children.length > 0) {
          node.children.forEach(addNodesToMap);
        }
      };
      
      // Build the map of existing nodes
      attributeTrees.forEach((tree: TreeNode) => {
        addNodesToMap(tree);
      });
      
      console.log('Created new node map with size:', newNodeMap.size);
      
      // Only update the node map if it's different from the current one
      if (newNodeMap.size !== nodeMap.size) {
        console.log('Updating node map state with new map');
        setNodeMap(newNodeMap);
      } else {
        console.log('Node map size unchanged, skipping update');
      }
    }
  }, [attributeTrees]);

  // Function to create a composite key for node lookup
  const createNodeKey = (granular_data: string, data_access: string, position: string, positionValue?: number): string => {
    console.log('Creating node key with:', {
      granular_data,
      data_access,
      position,
      positionValue
    });
    
    // If granular_data already contains the value in parentheses, use it as is
    if (granular_data.includes('(')) {
      const key = `${granular_data}-${data_access}-${position}${positionValue ? `::${positionValue}` : ''}`;
      console.log('Created node key (existing format):', key);
      return key;
    }
    
    // Otherwise, construct the key in the backend format
    const key = `${granular_data}(*)-${data_access}-${position}${positionValue ? `::${positionValue}` : ''}`;
    console.log('Created node key (constructed format):', key);
    return key;
  };

  // Function to parse a node label and extract its value
  const parseNodeLabel = (label: string): { baseLabel: string, value: string | null } => {
    // If it's a chained label, only parse the first part
    if (label.includes('::')) {
      const firstPart = label.split('::')[0];
      const match = firstPart.match(/^(.*?)\((.*?)\)$/);
      if (match) {
        return {
          baseLabel: match[1],
          value: match[2]
        };
      }
    }
    
    // For non-chained labels, parse normally
    const match = label.match(/^(.*?)\((.*?)\)$/);
    if (match) {
      return {
        baseLabel: match[1],
        value: match[2]
      };
    }
    return {
      baseLabel: label,
      value: null
    };
  };

  // Function to create a hierarchical tree from a chained label
  const createTreeFromChainedLabel = (granular_data: string, access: string, position: string): TreeNode => {
    console.log('createTreeFromChainedLabel called with:');
    console.log('granular_data:', granular_data);
    console.log('access:', access);
    console.log('position:', position);
    
    const parts = parseLabel(granular_data);
    console.log('Parsed parts:', parts);
    
    if (parts.length === 0) {
      throw new Error('Cannot create tree from empty label');
    }

    // Find the original node in the attribute trees to get its children structure
    const findOriginalNode = (tree: TreeNode): TreeNode | undefined => {
      const { baseLabel: nodeBaseLabel } = parseNodeLabel(tree.label);
      if (nodeBaseLabel === parts[0].baseLabel) {
        return tree;
      }
      
      for (const child of tree.children) {
        const found = findOriginalNode(child);
        if (found) {
          return found;
        }
      }
      return undefined;
    };

    // Find the original node to get its children structure
    let originalNode: TreeNode | undefined;
    for (const tree of attributeTrees) {
      originalNode = findOriginalNode(tree);
      if (originalNode) {
        break;
      }
    }

    if (!originalNode) {
      throw new Error(`Could not find original node for ${parts[0].baseLabel}`);
    }

    // Create the root node
    const root: TreeNode = {
      label: parts[0].baseLabel,
      value: parts[0].value,
      access: access,
      position: position,
      children: []
    };

    // Track which part we're currently processing
    let currentPartIdx = 1;

    // Helper function to create a child node with appropriate value
    const createChildNode = (originalChild: TreeNode): TreeNode => {
      const childNode: TreeNode = {
        label: originalChild.label,
        value: '',
        access: access,
        position: position,
        children: []
      };

      // If this child matches the next part in our sequence
      if (currentPartIdx < parts.length && originalChild.label === parts[currentPartIdx].baseLabel) {
        childNode.value = parts[currentPartIdx].value;
        currentPartIdx++;
      }
      // For nodes after the last explicitly mentioned node, use ALL_VALUES
      else if (currentPartIdx >= parts.length) {
        childNode.value = '*';
      }
      // For intermediate nodes, use empty value
      else {
        childNode.value = '';
      }

      console.log('Created child node:', childNode.label, 'with value:', childNode.value);
      return childNode;
    };

    // Recursive function to build the tree
    const buildTree = (currentOriginalNode: TreeNode, currentRoot: TreeNode) => {
      // Process each child of the current original node
      for (const originalChild of currentOriginalNode.children) {
        const childNode = createChildNode(originalChild);
        currentRoot.children.push(childNode);
        
        // Recursively process the child's children
        if (originalChild.children && originalChild.children.length > 0) {
          buildTree(originalChild, childNode);
        }
      }
    };

    // Start building the tree from the root
    buildTree(originalNode, root);

    return root;
  };

  // Function to apply policies to the trees
  const applyPolicies = () => {
    if (attributeTrees.length === 0 || policies.length === 0) {
      return;
    }
    
    console.log('Starting to apply policies. Current attribute trees:', attributeTrees);
    console.log('Policies to apply:', policies);
    console.log('Current node map size:', nodeMap.size);
    
    // Create a deep copy of the trees to avoid mutating state directly
    const updatedTrees = JSON.parse(JSON.stringify(attributeTrees));
    
    // Track which policies we've already processed
    const processedPolicies = new Set<string>();
    
    // Track if any changes were made
    let changesMade = false;
    
    // Create a new node map to track changes
    const updatedNodeMap = new Map(nodeMap);
    
    // First, build a map of all existing nodes in the trees to check for duplicates
    const existingNodesMap = new Map<string, TreeNode>();
    
    const addNodesToMap = (node: TreeNode) => {
      const nodeKey = createNodeKey(node.label, node.access || '', node.position || '', node.positionValue || 1);
      console.log('Adding node to map:', {
        nodeLabel: node.label,
        nodeAccess: node.access,
        nodePosition: node.position,
        nodeKey
      });
      
      // Map the composite key to the full node data
      existingNodesMap.set(nodeKey, {
        ...node,
        value: node.value || '', // Ensure value is preserved
        access: node.access || '', // Ensure access is preserved
        position: node.position || '', // Ensure position is preserved
        positionValue: node.positionValue || 1 // Ensure positionValue is preserved
      });
      
      // Process children
      if (node.children && node.children.length > 0) {
        node.children.forEach(addNodesToMap);
      }
    };
    
    // Build the map of existing nodes
    updatedTrees.forEach((tree: TreeNode) => {
      addNodesToMap(tree);
    });
    
    console.log('Built map of existing nodes with size:', existingNodesMap.size);
    console.log('Existing node keys:', Array.from(existingNodesMap.keys()));
    
    // Apply each policy to the attribute trees
    policies.forEach(policy => {
      // Create a unique key for the policy
      const policyKey = `${policy.granular_data}-${policy.data_access}-${policy.position}-${policy.positionValue || 1}`;
      
      console.log('Processing policy:', policy);
      console.log('Policy key:', policyKey);
      console.log('Policy granular_data:', policy.granular_data);
      console.log('Policy data_access:', policy.data_access);
      console.log('Policy position:', policy.position);
      
      // Skip if we've already processed this policy
      if (processedPolicies.has(policyKey)) {
        console.log('Skipping already processed policy:', policy);
        return;
      }
      
      processedPolicies.add(policyKey);
      console.log('Applying policy:', policy);
      
      // Create composite key for node lookup
      const nodeKey = createNodeKey(policy.granular_data, policy.data_access, policy.position, policy.positionValue);
      
      console.log('Looking for node with key:', nodeKey);
      console.log('Node exists in map:', existingNodesMap.has(nodeKey));
      
      // Check if a node with these exact attributes exists in our map
      const existingNode = existingNodesMap.get(nodeKey);
      
      if (existingNode) {
        console.log('Found existing node with same attributes:', existingNode);
        return; // Node already exists with these exact attributes
      } else {
        console.log('Node not found with these attributes, creating new node:', policy.granular_data);
        
        // Parse the granular_data to get the base label
        const { baseLabel } = parseNodeLabel(policy.granular_data);
        
        // Find the parent node by searching through the existing attribute trees
        let parentNode: TreeNode | undefined;
        let parentTreeIndex = -1;
        
        // Helper function to search through a tree
        const findParentInTree = (tree: TreeNode, treeIndex: number): TreeNode | undefined => {
          console.log(`Searching in tree node: ${tree.label}`);
          console.log(`Looking for parent of node with label: ${baseLabel}`);
          console.log(`Current node's children:`, tree.children.map(child => child.label));
          
          // Check if any of this node's children match the policy's granular_data by label only
          const matchingChild = tree.children.find(child => {
            const { baseLabel: childBaseLabel } = parseNodeLabel(child.label);
            return childBaseLabel === baseLabel;
          });
          
          if (matchingChild) {
            console.log(`Found matching child with label: ${matchingChild.label}`);
            parentTreeIndex = treeIndex;
            return tree;
          }
          
          // Recursively search through children
          for (const child of tree.children) {
            console.log(`Recursively searching in child: ${child.label}`);
            const found = findParentInTree(child, treeIndex);
            if (found) {
              return found;
            }
          }
          return undefined;
        };
        
        // Search through all attribute trees
        for (let i = 0; i < attributeTrees.length; i++) {
          const tree = attributeTrees[i];
          parentNode = findParentInTree(tree, i);
          if (parentNode) {
            break;
          }
        }
        
        if (parentNode) {
          console.log('Found parent node:', parentNode);
          console.log('Parent tree index:', parentTreeIndex);
          
          // Create the new node tree from the chained label
          const newNodeTree = createTreeFromChainedLabel(
            policy.granular_data,
            policy.data_access.toLowerCase(),
            policy.position.toLowerCase()
          );
          
          // Add the new node tree to the parent in the updated trees
          if (parentTreeIndex >= 0 && parentTreeIndex < updatedTrees.length) {
            // Find the parent node in the updated trees
            const findParentInUpdatedTree = (tree: TreeNode): TreeNode | undefined => {
              if (tree.label === parentNode!.label) {
                return tree;
              }
              
              for (const child of tree.children) {
                const found = findParentInUpdatedTree(child);
                if (found) {
                  return found;
                }
              }
              return undefined;
            };
            
            const updatedParentNode = findParentInUpdatedTree(updatedTrees[parentTreeIndex]);
            
            if (updatedParentNode) {
              console.log('Found parent node in updated trees');
                
                // Check if the parent already has a child with the same composite key
                const existingChildIndex = updatedParentNode.children.findIndex(child => {
                const childKey = createNodeKey(child.label, child.access, child.position, child.positionValue || 1);
                const newKey = createNodeKey(newNodeTree.label, newNodeTree.access, newNodeTree.position, newNodeTree.positionValue || 1);
                  return childKey === newKey;
                });
                
                if (existingChildIndex >= 0) {
                  console.log(`Parent already has a child with the same composite key at index ${existingChildIndex}`);
                console.log('Replacing existing child with new node tree');
                updatedParentNode.children[existingChildIndex] = newNodeTree;
                } else {
                console.log('Adding new node tree to parent');
                updatedParentNode.children.push(newNodeTree);
                }
                
              // Add all nodes in the tree to our map
                const addNodesToNodeMap = (node: TreeNode) => {
                const nodeKey = createNodeKey(node.label, node.access, node.position, node.positionValue || 1);
                  updatedNodeMap.set(nodeKey, node);
                  
                  if (node.children && node.children.length > 0) {
                    node.children.forEach(addNodesToNodeMap);
                  }
                };
                
              addNodesToNodeMap(newNodeTree);
                
                // Mark that changes were made
                changesMade = true;
                
              console.log('Added new node tree to parent and node map');
                console.log('New node map size:', updatedNodeMap.size);
            } else {
              console.error('Could not find parent node in updated trees');
            }
          } else {
            console.error('Invalid parent tree index:', parentTreeIndex);
          }
        } else {
          console.log(`No suitable parent node found for "${baseLabel}" in the attribute trees`);
          console.log('Creating a new root node for this policy');
          
          // Create a new root node tree from the chained label
          const newRootNodeTree = createTreeFromChainedLabel(
            policy.granular_data,
            policy.data_access.toLowerCase(),
            policy.position.toLowerCase()
          );
            
            // Check if a root node with the same composite key already exists
            const existingRootIndex = updatedTrees.findIndex((tree: TreeNode) => {
            const treeKey = createNodeKey(tree.label, tree.access, tree.position, tree.positionValue || 1);
            const newKey = createNodeKey(newRootNodeTree.label, newRootNodeTree.access, newRootNodeTree.position, newRootNodeTree.positionValue || 1);
              return treeKey === newKey;
            });
            
            if (existingRootIndex >= 0) {
              console.log(`Root node with the same composite key already exists at index ${existingRootIndex}`);
            console.log('Replacing existing root with new node tree');
            updatedTrees[existingRootIndex] = newRootNodeTree;
            } else {
            console.log('Adding new root node tree to trees');
            updatedTrees.push(newRootNodeTree);
            }
            
          // Add all nodes in the tree to our map
            const addNodesToNodeMap = (node: TreeNode) => {
            const nodeKey = createNodeKey(node.label, node.access, node.position, node.positionValue || 1);
              updatedNodeMap.set(nodeKey, node);
              
              if (node.children && node.children.length > 0) {
                node.children.forEach(addNodesToNodeMap);
              }
            };
            
          addNodesToNodeMap(newRootNodeTree);
            
            // Mark that changes were made
            changesMade = true;
            
          console.log('Added new root node tree to trees and node map');
            console.log('New node map size:', updatedNodeMap.size);
        }
      }
    });
    
    console.log('Finished applying policies. Updated trees:', updatedTrees);
    console.log('Final node map size:', updatedNodeMap.size);
    
    // Only update the state if there are actual changes
    if (changesMade) {
      console.log('Changes detected, updating state');
      setAttributeTrees(updatedTrees);
      
      // Update the node map state to trigger a re-render
      setNodeMap(updatedNodeMap);
    } else {
      console.log('No changes detected, skipping state update');
    }
  };

  // Request policy update from the backend
  const requestPolicyUpdate = () => {
    if (socket && socket.connected) {
      console.log('Requesting policy update from backend');
      socket.emit('request_policy_update');
      // Apply policies after requesting update
      applyPolicies();
    } else {
      console.warn('Socket not connected, cannot request policy update');
    }
  };

  // Fetch attribute trees and policies
  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        
        // Use the full URL if we're in production, otherwise use the relative path
        const port = import.meta.env.VITE_PORT || 5000;
        const baseUrl = import.meta.env.PROD 
          ? `http://localhost:${port}` 
          : `http://localhost:${port}`;
        
        // Fetch attribute trees
        console.log('Fetching attribute trees from:', `${baseUrl}/get_attribute_trees`);
        const treesResponse = await fetch(`${baseUrl}/get_attribute_trees`);
        
        if (!treesResponse.ok) {
          const errorText = await treesResponse.text();
          console.error('Error response text:', errorText);
          throw new Error(`Failed to fetch attribute trees: ${treesResponse.status} ${treesResponse.statusText}`);
        }
        
        const treesData = await treesResponse.json();
        console.log('Received attribute trees:', treesData);
        
        // Fetch policies
        console.log('Fetching policies from:', `${baseUrl}/get_policies`);
        const policiesResponse = await fetch(`${baseUrl}/get_policies`);
        
        if (!policiesResponse.ok) {
          const errorText = await policiesResponse.text();
          console.error('Error response text:', errorText);
          throw new Error(`Failed to fetch policies: ${policiesResponse.status} ${policiesResponse.statusText}`);
        }
        
        const policiesData = await policiesResponse.json();
        console.log('Received policies:', policiesData);
        
        // Set state
        setAttributeTrees(treesData.attribute_trees || []);
        setPolicies(policiesData.policies || []);
        setIsLoading(false);
        
        // Apply policies after fetching data
        console.log('Applying policies after fetching data');
        setTimeout(() => {
          applyPolicies();
        }, 100);
      } catch (err) {
        console.error('Error fetching data:', err);
        setError(err instanceof Error ? err.message : String(err));
        setIsLoading(false);
      }
    };
    
    fetchData();
  }, []);

  // Helper function to find the parent node of a given node
  const findParentNode = (trees: TreeNode[], targetNode: TreeNode): TreeNode | null => {
    // Helper function to search recursively through a tree
    const searchTree = (node: TreeNode): TreeNode | null => {
      // Check if this node is the parent of the target node
      if (node.children && node.children.includes(targetNode)) {
        return node;
      }
      
      // Check children
      if (node.children && node.children.length > 0) {
        for (const child of node.children) {
          const result = searchTree(child);
          if (result) {
            return result;
          }
        }
      }
      
      return null;
    };
    
    // Search through all trees
    for (const tree of trees) {
      const result = searchTree(tree);
      if (result) {
        return result;
      }
    }
    
    return null;
  };

  const handleAccessChange = (node: TreeNode, value: string) => {
    // Create a deep copy of the appropriate trees based on view mode
    const treesToUpdate = viewMode === 'edit' ? editViewTrees : attributeTrees;
    const updatedTrees = JSON.parse(JSON.stringify(treesToUpdate));
    
    // Function to update the node in the tree
    const updateNode = (trees: TreeNode[]): boolean => {
      for (let i = 0; i < trees.length; i++) {
        if (trees[i].label === node.label) {
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
    
    // Update the appropriate state based on view mode
    if (viewMode === 'edit') {
      setEditViewTrees(updatedTrees);
    } else {
    setAttributeTrees(updatedTrees);
    }
    
    console.log('Access updated:', node.label, value);
  };
  
  const handlePositionChange = (node: TreeNode, value: string, positionValue?: number) => {
    // Create a deep copy of the appropriate trees based on view mode
    const treesToUpdate = viewMode === 'edit' ? editViewTrees : attributeTrees;
    const updatedTrees = JSON.parse(JSON.stringify(treesToUpdate));
    
    // Function to update the node in the tree
    const updateNode = (trees: TreeNode[]): boolean => {
      for (let i = 0; i < trees.length; i++) {
        if (trees[i].label === node.label) {
          trees[i] = {
            ...trees[i],
            position: value,
            positionValue: positionValue || 1
          };
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
    
    // Update the appropriate state based on view mode
    if (viewMode === 'edit') {
      setEditViewTrees(updatedTrees);
    } else {
    setAttributeTrees(updatedTrees);
    }
    
    console.log('Position updated:', node.label, value, positionValue);
  };

  const handleValueChange = (node: TreeNode, value: string) => {
    // Create a deep copy of the appropriate trees based on view mode
    const treesToUpdate = viewMode === 'edit' ? editViewTrees : attributeTrees;
    const updatedTrees = JSON.parse(JSON.stringify(treesToUpdate));
    
    // Function to update the node in the tree
    const updateNode = (trees: TreeNode[]): boolean => {
      for (let i = 0; i < trees.length; i++) {
        if (trees[i].label === node.label) {
          trees[i].value = value;
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
    
    // Update the appropriate state based on view mode
    if (viewMode === 'edit') {
      setEditViewTrees(updatedTrees);
    } else {
    setAttributeTrees(updatedTrees);
    }
    
    console.log('Value updated:', node.label, value);
  };

  useEffect(() => {
    if (shouldApplyPolicies) {
      applyPolicies();
      setShouldApplyPolicies(false);
    }
  }, [shouldApplyPolicies, attributeTrees, policies]);

  const handleSubmitChanges = async () => {
    try {
      setIsLoading(true);
      const port = import.meta.env.VITE_PORT || 5000;
      
      // If there's text in the policy text box, submit that first
      if (policyText.trim()) {
        const apiUrl = import.meta.env.PROD 
          ? `http://localhost:${port}/add_policy_from_text` 
          : `http://localhost:${port}/add_policy_from_text`;
        const textResponse = await fetch(apiUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ policy_text: policyText }),
        });
        
        if (!textResponse.ok) {
          const error = await textResponse.json();
          throw new Error(error.error || 'Failed to add policy from text');
        }
        
        setPolicyText(''); // Clear the text input
      }
      
      // Find all modified nodes from edit view trees
      const modifiedNodes: TreeNode[] = [];
      const processedNodes = new Set<string>(); // Track nodes we've already processed
      
      const findModifiedNodes = (node: TreeNode) => {
        // If this node has non-default values, add it
        if (node.value !== '' && node.value !== 'default' && (node.access || node.position)) {
          modifiedNodes.push(node);
        }
        
        // Check children
        if (node.children && node.children.length > 0) {
          node.children.forEach(findModifiedNodes);
        }
      };
      
      // Search through edit view trees
      editViewTrees.forEach(findModifiedNodes);
      
      console.log('Found modified nodes:', modifiedNodes);
      
      // Create policies for modified nodes
      const policyPromises: Promise<Response>[] = [];
      
      modifiedNodes.forEach(node => {
        // Skip if we've already processed this node as part of a chain
        if (processedNodes.has(node.label)) return;
        
        // Find chainable children
        const chainableChildren = findChainableChildren(node, editViewTrees);
        
        if (chainableChildren.length > 0) {
          // Create combined policies for each chainable child
          chainableChildren.forEach(child => {
            const policyData = {
              granular_data: createCombinedLabel(node, child),
              data_access: node.access,
              position: node.position === "Current" ? "Current" : `${node.position}::${node.positionValue || 1}`
            };
            
            const apiUrl = import.meta.env.PROD 
              ? `http://localhost:${port}/add_policy` 
              : `http://localhost:${port}/add_policy`;
            
            policyPromises.push(
              fetch(apiUrl, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify(policyData),
              })
            );
            
            // Mark both nodes as processed
            processedNodes.add(node.label);
            processedNodes.add(child.label);
          });
        } else {
          // Create regular policy for non-chainable node
          const policyData = {
            granular_data: node.label.includes('(') ? node.label : `${node.label}(${node.value || ''})`,
            data_access: node.access,
            position: node.position === "Current" ? "Current" : `${node.position}::${node.positionValue || 1}`
          };
          
          const apiUrl = import.meta.env.PROD 
            ? `http://localhost:${port}/add_policy` 
            : `http://localhost:${port}/add_policy`;
          
          policyPromises.push(
            fetch(apiUrl, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify(policyData),
            })
          );
          
          processedNodes.add(node.label);
        }
      });
      
      // Wait for all policies to be added
      await Promise.all(policyPromises);
      
      // After all policies are added, fetch updated data
      const baseUrl = import.meta.env.PROD 
        ? `http://localhost:${port}` 
        : `http://localhost:${port}`;
      
      // Fetch updated attribute trees and policies
      const [treesData, policiesData] = await Promise.all([
        fetch(`${baseUrl}/get_attribute_trees`).then(res => res.json()),
        fetch(`${baseUrl}/get_policies`).then(res => res.json())
      ]);
      
      // Update the main trees with new data from backend
      setAttributeTrees(treesData.attribute_trees || []);
      setPolicies(policiesData.policies || []);
      
      // Trigger policy application
      setShouldApplyPolicies(true);
      
      // Switch to permitted view to see the changes
      setViewMode('permitted');
      
    } catch (err) {
      console.error('Error submitting changes:', err);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  };

  const renderTree = (tree: TreeNode, index: number) => (
    <Box key={index} p={2} borderRadius="md" bg="white" boxShadow="sm">
      <TreeView 
        data={tree} 
        isRoot={true}
        viewMode={viewMode}
        onAccessChange={viewMode === 'edit' ? handleAccessChange : undefined}
        onPositionChange={viewMode === 'edit' ? handlePositionChange : undefined}
        onValueChange={viewMode === 'edit' ? handleValueChange : undefined}
        onDelete={handleDeletePolicy}
        highlightedPolicy={highlightedPolicy}
      />
    </Box>
  );
  
  // Get the complete chained label from the root node, including values
  const getCompleteLabel = (node: TreeNode): string => {
    let result = '';
    const nodesWithAllValues: string[] = [];
    const queue: TreeNode[] = [node];
    
    while (queue.length > 0) {
      const current = queue.shift()!;
      console.log('Processing node:', current.label, 'with value:', current.value);
      
      if (current.value === '') {
        // Skip empty values
      } else if (current.value === '*') {
        // Collect nodes with all values
        nodesWithAllValues.push(current.label);
      } else {
        // If we have collected any all-value nodes, add them first
        if (nodesWithAllValues.length > 0) {
          if (result) result += '::';
          result += nodesWithAllValues.map(label => `${label}(*)`).join('::');
          nodesWithAllValues.length = 0; // Clear the array
        }
        
        // Add the current node with its value
        if (result) result += '::';
        result += `${current.label}(${current.value})`;
      }
      
      // Add children to queue
      if (current.children && current.children.length > 0) {
        queue.push(...current.children);
      }
    }
    
    if (result === '') {
      result = nodesWithAllValues[0] + '(*)';
    }

    console.log('Generated label:', result);
    return result;
  };

  // Function to handle policy deletion
  const handleDeletePolicy = async (policyData: any) => {
    try {
      setIsLoading(true);
      console.log('Starting policy deletion with node:', policyData);
      const granularData = getCompleteLabel(policyData);
      console.log('Generated granular_data:', granularData);

      // Transform the policy data into the format expected by the backend
      const transformedPolicyData = {
        granular_data: granularData.toLowerCase(),
        data_access: policyData.access.toLowerCase(),
        position: policyData.position === "Current" ? "Current" : 
                 policyData.position.includes('(') ? policyData.position : 
                 `${policyData.position}::${policyData.positionValue || 1}`
      };
      
      console.log('Deleting policy with data:', transformedPolicyData);
      
      // Send delete request to backend
      const port = import.meta.env.VITE_PORT || 5000;
      const apiUrl = import.meta.env.PROD 
        ? `http://localhost:${port}/delete_policy` 
        : `http://localhost:${port}/delete_policy`;
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(transformedPolicyData),
      });

      if (!response.ok) {
        throw new Error(`Failed to delete policy: ${response.status} ${response.statusText}`);
      }

      // After successful deletion, fetch updated data
      const baseUrl = import.meta.env.PROD 
        ? `http://localhost:${port}` 
        : `http://localhost:${port}`;
      
      // Fetch both attribute trees and policies in parallel
      const [treesData, policiesData] = await Promise.all([
        fetch(`${baseUrl}/get_attribute_trees`).then(res => res.json()),
        fetch(`${baseUrl}/get_policies`).then(res => res.json())
      ]);

      // Update state with new data
      setAttributeTrees(treesData.attribute_trees || []);
      setPolicies(policiesData.policies || []);
      
      // Trigger policy application after state updates
      setShouldApplyPolicies(true);
    } catch (err) {
      console.error('Error deleting policy:', err);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  };

  // Function to parse any label into its components (treats single labels as chains of length 1)
  const parseLabel = (label: string): { baseLabel: string, value: string }[] => {
    // Split by :: to handle both single and chained labels
    const parts = label.split('::');
    return parts.map(part => {
      const match = part.match(/^(.*?)\((.*?)\)$/);
      if (match) {
        return {
          baseLabel: match[1],
          value: match[2]
        };
      }
      return {
        baseLabel: part,
        value: ''
      };
    });
  };

  // Function to filter nodes based on the view mode
  const filterNodes = (node: TreeNode): TreeNode | null => {
    // If we're in 'all' view, return the node as is with all its properties
    if (viewMode === 'all') {
      const filteredNode: TreeNode = {
        ...node,
        children: []
      };

      // Recursively filter children while preserving all properties
      if (node.children && node.children.length > 0) {
        node.children.forEach(child => {
          const filteredChild = filterNodes(child);
          if (filteredChild) {
            filteredNode.children.push(filteredChild);
          }
        });
      }

      return filteredNode;
    }

    // If we're in 'permitted' view, show nodes with permissions and maintain hierarchy
    if (viewMode === 'permitted') {
      // Create a copy of the node to avoid modifying the original
      const filteredNode: TreeNode = {
        label: node.label,
        value: node.value,
        access: node.access,
        position: node.position,
        children: []
      };

      // If this node has access and position, it's part of a permission chain
      const isPartOfPermissionChain = node.access && node.position;

      // If this node has a value or is part of a permission chain, process its children
      if (node.value !== '' || isPartOfPermissionChain) {
        if (node.children && node.children.length > 0) {
          node.children.forEach(child => {
            const filteredChild = filterNodes(child);
            if (filteredChild) {
              filteredNode.children.push(filteredChild);
            }
          });
        }

        // Only return the node if it has children or is part of a permission chain
        if (filteredNode.children.length > 0 || isPartOfPermissionChain) {
          return filteredNode;
        }
      }

      return null;
    }

    // If we're in 'edit' view, show all nodes
    if (viewMode === 'edit') {
      const filteredNode: TreeNode = {
        ...node,
        children: []
      };

      if (node.children && node.children.length > 0) {
        node.children.forEach(child => {
          const filteredChild = filterNodes(child);
          if (filteredChild) {
            filteredNode.children.push(filteredChild);
          }
        });
      }

      return filteredNode;
    }

    return node;
  };

  // Function to get all permission nodes with their complete subtrees
  const getAllPermissionNodes = (trees: TreeNode[]): TreeNode[] => {
    const permissionNodes: TreeNode[] = [];
    
    // Helper function to find a node by label in a tree
    const findNodeByLabel = (tree: TreeNode, label: string): TreeNode | null => {
      if (tree.label === label) {
        return tree;
      }
      for (const child of tree.children) {
        const found = findNodeByLabel(child, label);
        if (found) {
          return found;
        }
      }
      return null;
    };

    // Helper function to find path between two nodes
    const findPath = (start: TreeNode, end: TreeNode): TreeNode[] => {
      const path: TreeNode[] = [];
      let current: TreeNode | null = end;
      
      while (current && current !== start) {
        path.unshift(current);
        // Find parent of current node
        const findParent = (tree: TreeNode): TreeNode | null => {
          if (tree.children.includes(current!)) {
            return tree;
          }
          for (const child of tree.children) {
            const parent = findParent(child);
            if (parent) {
              return parent;
            }
          }
          return null;
        };
        
        current = findParent(start);
      }
      if (current === start) {
        path.unshift(start);
      }
      return path;
    };

    // Process each policy
    policies.forEach(policy => {
      const parts = policy.granular_data.split('::').map(part => {
        const [label, value] = part.split('(');
        return {
          label,
          value: value ? value.replace(')', '') : ''
        };
      });

      if (parts.length === 0) return;

      // Find the first node in the policy chain
      let firstNode: TreeNode | null = null;
      for (const tree of trees) {
        firstNode = findNodeByLabel(tree, parts[0].label);
        if (firstNode) break;
      }

      if (!firstNode) return;

      // Create the root node for the permission chain
      const rootNode: TreeNode = {
        label: firstNode.label,
        value: parts[0].value,
        access: policy.data_access,
        position: policy.position.split('::')[0],
        positionValue: policy.position.includes('::') ? parseInt(policy.position.split('::')[1]) : 1,
        children: []
      };

      // Process each subsequent part in the chain
      let currentNode = firstNode;
      for (let i = 1; i < parts.length; i++) {
        // Find the next node in the chain
        const nextNode = findNodeByLabel(currentNode, parts[i].label);
        if (!nextNode) break;

        // Find the path between current and next node
        const path = findPath(currentNode, nextNode);
        
        // Create nodes for the path
        let currentParent = rootNode;
        for (let j = 1; j < path.length; j++) {
          const pathNode = path[j];
          const newNode: TreeNode = {
            label: pathNode.label,
            value: pathNode === nextNode ? parts[i].value : '',
            access: policy.data_access,
            position: policy.position.split('::')[0],
            positionValue: policy.position.includes('::') ? parseInt(policy.position.split('::')[1]) : 1,
            children: []
          };

          // Add to the last child of currentParent
          let lastChild = currentParent;
          while (lastChild.children.length > 0) {
            lastChild = lastChild.children[lastChild.children.length - 1];
          }
          lastChild.children.push(newNode);
          currentParent = newNode;
        }

        currentNode = nextNode;
      }

      // Add all children of the last node as "All Values"
      if (currentNode.children.length > 0) {
        let lastNode = rootNode;
        while (lastNode.children.length > 0) {
          lastNode = lastNode.children[lastNode.children.length - 1];
        }

        currentNode.children.forEach(child => {
          lastNode.children.push({
            label: child.label,
            value: '*',
            access: policy.data_access,
            position: policy.position.split('::')[0],
            positionValue: policy.position.includes('::') ? parseInt(policy.position.split('::')[1]) : 1,
            children: []
          });
        });
      }

      permissionNodes.push(rootNode);
    });

    return permissionNodes;
  };

  // Helper function to check if two nodes can form a chain
  const isChainable = (parent: TreeNode, child: TreeNode): boolean => {
    return parent.value !== '' && 
           child.value !== '' && 
           parent.access === child.access && 
           parent.position === child.position;
  };

  // Helper function to create a combined label
  const createCombinedLabel = (parent: TreeNode, child: TreeNode): string => {
    const parentLabel = parent.label.includes('(') ? parent.label : `${parent.label}(${parent.value})`;
    const childLabel = child.label.includes('(') ? child.label : `${child.label}(${child.value})`;
    return `${parentLabel}::${childLabel}`;
  };

  // Helper function to find chainable children
  const findChainableChildren = (node: TreeNode, trees: TreeNode[]): TreeNode[] => {
    const chainableChildren: TreeNode[] = [];
    
    const traverse = (currentNode: TreeNode) => {
      if (currentNode.children && currentNode.children.length > 0) {
        currentNode.children.forEach(child => {
          if (isChainable(node, child)) {
            if (node.label !== child.label) {
              chainableChildren.push(child);
            }
          }
          traverse(child);
        });
      }
    };
    
    trees.forEach(traverse);
    return chainableChildren;
  };

  // Function to convert a permission to text
  const convertPermissionToText = async (node: TreeNode): Promise<string> => {
    try {
      const granularData = getCompleteLabel(node);
      const policyData = {
        granular_data: granularData.toLowerCase(),
        data_access: node.access.toLowerCase(),
        position: node.position.toLowerCase()
      };

      const port = import.meta.env.VITE_PORT || 5000;
      const apiUrl = import.meta.env.PROD 
        ? `http://localhost:${port}/convert_to_text` 
        : `http://localhost:${port}/convert_to_text`;
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(policyData),
      });

      if (!response.ok) {
        throw new Error(`Failed to convert policy to text: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return data.text;
    } catch (err) {
      console.error('Error converting policy to text:', err);
      return `Error converting policy to text: ${err instanceof Error ? err.message : String(err)}`;
    }
  };

  // Function to convert all permissions to text
  const convertAllPermissionsToText = async () => {
    try {
      setIsLoading(true);
      const permissionNodes = getAllPermissionNodes(attributeTrees);
      const texts = await Promise.all(permissionNodes.map(convertPermissionToText));
      setPermissionTexts(texts);
    } catch (err) {
      console.error('Error converting permissions to text:', err);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  };

  // Update text view when permissions change
  useEffect(() => {
    if (displayMode === 'text' && viewMode === 'permitted') {
      convertAllPermissionsToText();
    }
  }, [displayMode, viewMode, attributeTrees]);

  const handlePolicyTextSubmit = async () => {
    if (!policyText.trim()) return;
    
    try {
      const port = import.meta.env.VITE_PORT || 5000;
      const apiUrl = import.meta.env.PROD 
        ? `http://localhost:${port}/add_policy_from_text` 
        : `http://localhost:${port}/add_policy_from_text`;
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ policy_text: policyText }),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to add policy');
      }
      
      const result = await response.json();
      setPolicyText(''); // Clear the input on success
      // The policy update will be handled by the socket.io event
    } catch (error) {
      console.error('Error adding policy from text:', error);
      // Handle error (show notification, etc.)
    }
  };

  // Handler to send mode to backend
  const handleModeChange = (mode: string) => {
    console.log("Setting mode in backend:", mode);
    const port = import.meta.env.VITE_PORT || 5000;
    fetch(`http://localhost:${port}/set_permission_mode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode }),
    });
  };

  return (
    <div className={styles.chatContainer}>
      <Box className={styles.messagesContainer} overflow="auto">
        <HStack justify="space-between" mb={4}>
          <HStack justify="space-between" align="center" width="100%">
            <Text 
              fontSize="xl" 
              fontWeight="bold" 
              color="brand.800"
              letterSpacing="tight"
              textTransform="uppercase"
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
              Permissions Manager
            </Text>
            <Box flexShrink={0}><PermissionModeSelector compact label="Mode:" onModeChange={handleModeChange} /></Box>
          </HStack>
        </HStack>

        <Box mb={4}>
          <HStack spacing={0} borderBottom="2px solid" borderColor="gray.200">
            <Button
              size="md"
              flex={1}
              colorScheme={viewMode === 'all' ? 'blue' : 'gray'}
              variant={viewMode === 'all' ? 'solid' : 'ghost'}
              onClick={() => handleViewModeChange('all')}
              borderTopRadius="md"
              borderBottomRadius="none"
              borderRight="1px solid"
              borderColor="gray.200"
              _hover={{
                bg: viewMode === 'all' ? 'blue.500' : 'gray.100'
              }}
              transition="all 0.2s"
            >
              Data Schema
            </Button>
            <Button
              size="md"
              flex={1}
              colorScheme={viewMode === 'permitted' ? 'blue' : 'gray'}
              variant={viewMode === 'permitted' ? 'solid' : 'ghost'}
              onClick={() => handleViewModeChange('permitted')}
              borderTopRadius="md"
              borderBottomRadius="none"
              borderRight="1px solid"
              borderLeft="1px solid"
              borderColor="gray.200"
              _hover={{
                bg: viewMode === 'permitted' ? 'blue.500' : 'gray.100'
              }}
              transition="all 0.2s"
            >
              Active Permissions
            </Button>
            <Button
              size="md"
              flex={1}
              colorScheme={viewMode === 'edit' ? 'blue' : 'gray'}
              variant={viewMode === 'edit' ? 'solid' : 'ghost'}
              onClick={() => handleViewModeChange('edit')}
              borderTopRadius="md"
              borderBottomRadius="none"
              borderRight="1px solid"
              borderLeft="1px solid"
              borderColor="gray.200"
              _hover={{
                bg: viewMode === 'edit' ? 'blue.500' : 'gray.100'
              }}
              transition="all 0.2s"
            >
              Create Permissions
            </Button>
            <Button
              size="md"
              flex={0.5}
              colorScheme={viewMode === 'logs' ? 'blue' : 'gray'}
              variant={viewMode === 'logs' ? 'solid' : 'ghost'}
              onClick={() => handleViewModeChange('logs')}
              borderTopRadius="md"
              borderBottomRadius="none"
              borderLeft="1px solid"
              borderColor="gray.200"
              _hover={{
                bg: viewMode === 'logs' ? 'blue.500' : 'gray.100'
              }}
              transition="all 0.2s"
            >
              Logs
            </Button>
          </HStack>
        </Box>

        {viewMode === 'permitted' && (
          <Box mb={4}>
            <HStack spacing={0} borderBottom="2px solid" borderColor="gray.200" justify="flex-start">
              <Button
                size="sm"
                height="32px"
                fontSize="sm"
                leftIcon={<MdAccountTree size={16} />}
                colorScheme={displayMode === 'tree' ? 'blue' : 'gray'}
                variant={displayMode === 'tree' ? 'solid' : 'ghost'}
                onClick={() => setDisplayMode('tree')}
                borderTopRadius="md"
                borderBottomRadius="none"
                borderRight="1px solid"
                borderColor="gray.200"
                _hover={{
                  bg: displayMode === 'tree' ? 'blue.500' : 'gray.100'
                }}
                transition="all 0.2s"
              >
                Tree View
              </Button>
              <Button
                size="sm"
                height="32px"
                fontSize="sm"
                leftIcon={<MdTextFields size={16} />}
                colorScheme={displayMode === 'text' ? 'blue' : 'gray'}
                variant={displayMode === 'text' ? 'solid' : 'ghost'}
                onClick={() => setDisplayMode('text')}
                borderTopRadius="md"
                borderBottomRadius="none"
                borderLeft="1px solid"
                borderColor="gray.200"
                _hover={{
                  bg: displayMode === 'text' ? 'blue.500' : 'gray.100'
                }}
                transition="all 0.2s"
              >
                Text View
              </Button>
            </HStack>
          </Box>
        )}
        
        {isLoading && (
          <Box textAlign="center" py={4}>
            <Spinner size="md" />
            <Text mt={2}>Loading...</Text>
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
        
        {!isLoading && !error && attributeTrees.length === 0 && (
          <Box p={3} borderRadius="md" bg="gray.50">
            <Text>No attribute trees available yet.</Text>
          </Box>
        )}
        
        {!isLoading && !error && attributeTrees.length > 0 && (
          <VStack align="stretch" spacing={2} width="100%">
            {viewMode === 'logs' ? (
              <LogsView />
            ) : viewMode === 'permitted' && displayMode === 'text' ? (
              <VStack align="stretch" spacing={4}>
                {permissionTexts.length > 0 ? (
                  permissionTexts.map((text, index) => (
                    <Box key={index} p={4} borderRadius="md" bg="white" boxShadow="sm">
                      <Text>{text}</Text>
                    </Box>
                  ))
                ) : (
                  <Box p={8} textAlign="center" bg="gray.50" borderRadius="md">
                    <Text color="gray.500" fontSize="lg">No active permissions</Text>
                  </Box>
                )}
              </VStack>
            ) : viewMode === 'permitted' ? (
              getAllPermissionNodes(attributeTrees).length > 0 ? (
                getAllPermissionNodes(attributeTrees).map((tree, index) => renderTree(tree, index))
              ) : (
                <Box p={8} textAlign="center" bg="gray.50" borderRadius="md">
                  <Text color="gray.500" fontSize="lg">No active permissions</Text>
                </Box>
              )
            ) : viewMode === 'edit' ? (
              <>
                {editViewTrees.map((tree, index) => {
                  const filteredTree = filterNodes(tree);
                  return filteredTree ? renderTree(filteredTree, index) : null;
                })}
                <Box mt={4}>
                  <Text 
                    fontSize="lg" 
                    fontWeight="bold" 
                    mb={2}
                    color="brand.800"
                    letterSpacing="tight"
                    textTransform="uppercase"
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
                    Create New Permission
                  </Text>
                  <Box width="100%" mb={4}>
                    <textarea
                      value={policyText}
                      onChange={(e) => setPolicyText(e.target.value)}
                      placeholder="Enter permission text here..."
                      style={{
                        width: '100%',
                        minHeight: '100px',
                        padding: '12px',
                        fontSize: '14px',
                        borderRadius: '6px',
                        border: '1px solid #E2E8F0',
                        resize: 'vertical',
                        fontFamily: 'inherit'
                      }}
                    />
                  </Box>
                  <Box textAlign="right">
                    <Button 
                      size="md" 
                      colorScheme="purple" 
                      onClick={handleSubmitChanges}
                      isLoading={isLoading}
                      _hover={{
                        bg: 'purple.600',
                        transform: 'translateY(-1px)',
                        boxShadow: 'lg'
                      }}
                      _active={{
                        bg: 'purple.700',
                        transform: 'translateY(0)'
                      }}
                    >
                      Submit Changes
                    </Button>
                  </Box>
                </Box>
              </>
            ) : (
              attributeTrees.map((tree, index) => {
                const filteredTree = filterNodes(tree);
                return filteredTree ? renderTree(filteredTree, index) : null;
              })
            )}
          </VStack>
        )}
      </Box>
    </div>
  );
};

export default PermissionChat; 
