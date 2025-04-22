/** @jsxImportSource @emotion/react */
import React, { useState, useEffect, useRef } from 'react'
import { Box, Text, VStack, Spinner, Select, HStack, Badge, Button, Switch, Input, IconButton } from '@chakra-ui/react'
import { FaFolder, FaFolderOpen, FaFile, FaTrash } from 'react-icons/fa'
import styles from './Chat.module.css'
import { io, Socket } from 'socket.io-client'

interface TreeNode {
  label: string;
  value: string;
  access: string;
  position: string;
  children: TreeNode[];
}

interface Policy {
  granular_data: string;
  data_access: string;
  position: string;
}

interface TreeViewProps {
  data: TreeNode;
  isRoot: boolean;
  viewMode: ViewMode;
  onAccessChange?: (node: TreeNode, newAccess: string) => void;
  onPositionChange?: (node: TreeNode, newPosition: string) => void;
  onValueChange?: (node: TreeNode, newValue: string) => void;
  onDelete?: (node: TreeNode) => void;
}

interface Message {
  role: string;
  content: string;
}

type ViewMode = 'permitted' | 'edit' | 'all';

const TreeView: React.FC<TreeViewProps> = ({ 
  data, 
  isRoot = false,
  viewMode,
  onAccessChange,
  onPositionChange,
  onValueChange,
  onDelete
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isEditingValue, setIsEditingValue] = useState(false);
  const [editedValue, setEditedValue] = useState(data.value);
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
          {data.label}
        </Text>
        
        <HStack ml="auto" spacing={2}>
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
                ml={1}
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
            <Badge colorScheme="green" ml={1}>
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
              <option value="read">Read</option>
              <option value="write">Write</option>
            </Select>
          ) : (
            <Badge colorScheme="blue" ml={1}>
              {data.access ? data.access.toUpperCase() : "Access"}
            </Badge>
          )}
          
          {/* Position badge/select */}
          {onPositionChange ? (
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
          ) : (
            <Badge colorScheme="purple" ml={1}>
              {data.position ? data.position.toUpperCase() : "Position"}
            </Badge>
          )}

          {/* Delete button - only show in all permission view */}
          {isRoot && onDelete && viewMode === 'permitted' && (
            <IconButton
              size="xs"
              colorScheme="red"
              aria-label="Delete policy"
              icon={<FaTrash />}
              onClick={handleDelete}
            />
          )}
        </HStack>
      </Box>
      
      {isOpen && hasChildren && (
        <Box ml={4} borderLeftWidth="1px" borderLeftColor="gray.200" pl={2}>
          {data.children.map((child, index) => (
            <TreeView
              key={index} 
              data={child}
              isRoot={false}
              viewMode={viewMode}
              onAccessChange={onAccessChange}
              onPositionChange={onPositionChange}
              onValueChange={onValueChange}
              onDelete={onDelete}
            />
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
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [socket, setSocket] = useState<Socket | null>(null);
  const [nodeMap, setNodeMap] = useState<Map<string, TreeNode>>(new Map());
  const [viewMode, setViewMode] = useState<ViewMode>('permitted');
  const [editModeTrees, setEditModeTrees] = useState<TreeNode[]>([]);

  // Initialize socket connection
  useEffect(() => {
    // Use the full URL if we're in production, otherwise use the relative path
    const baseUrl = import.meta.env.PROD 
      ? 'http://localhost:5000' 
      : 'http://localhost:5000';
    
    console.log('Initializing socket connection to:', baseUrl);
    const newSocket = io(baseUrl);
    
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
        // Parse the node label to get the base label and value
        const { baseLabel, value } = parseNodeLabel(node.label);
        
        // Create a composite key using all attributes
        const nodeKey = `${baseLabel}:${value || ''}:${node.access || ''}:${node.position || ''}`;
        
        // Map the composite key to the full node data
        newNodeMap.set(nodeKey, {
          ...node,
          label: baseLabel, // Use the base label without the value
          value: value || node.value || '', // Preserve existing value or use parsed value
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

  // Function to parse a node label and extract its value
  const parseNodeLabel = (label: string): { baseLabel: string, value: string | null } => {
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
      // Create a composite key using all attributes
      const nodeKey = `${node.label}:${node.value || ''}:${node.position || ''}:${node.access || ''}`;
      
      // Map the composite key to the full node data
      existingNodesMap.set(nodeKey, {
        ...node,
        value: node.value || '', // Ensure value is preserved
        access: node.access || '', // Ensure access is preserved
        position: node.position || '' // Ensure position is preserved
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
      const policyKey = `${policy.granular_data}-${policy.data_access}-${policy.position}`;
      
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
      
      // Parse the granular_data to separate label and value
      const { baseLabel, value } = parseNodeLabel(policy.granular_data);
      
      // Create composite key for node lookup using all attributes
      const nodeKey = `${baseLabel}:${value || '*'}:${policy.data_access.toLowerCase()}:${policy.position.toLowerCase()}`;
      
      console.log('Looking for node with key:', nodeKey);
      console.log('Node exists in map:', existingNodesMap.has(nodeKey));
      
      // Check if a node with these exact attributes exists in our map
      const existingNode = existingNodesMap.get(nodeKey);
      
      if (existingNode) {
        console.log('Found existing node with same attributes:', existingNode);
        return; // Node already exists with these exact attributes
      } else {
        console.log('Node not found with these attributes, creating new node:', baseLabel);
        
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
          
          // Create the new node
          const newNode: TreeNode = {
            label: baseLabel,
            value: value || '', // Use the value from the policy, or empty string if none
            children: [],
            access: policy.data_access.toLowerCase(),
            position: policy.position.toLowerCase()
          };
          
          // Add the new node to the parent in the updated trees
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
              
              // Find the original node in the attribute trees to get its children
              const findOriginalNode = (tree: TreeNode): TreeNode | undefined => {
                const { baseLabel: nodeBaseLabel } = parseNodeLabel(tree.label);
                if (nodeBaseLabel === baseLabel) {
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
              
              // Find the original node to get its children
              let originalNode: TreeNode | undefined;
              for (const tree of attributeTrees) {
                originalNode = findOriginalNode(tree);
                if (originalNode) {
                  break;
                }
              }
              
              if (originalNode) {
                console.log('Found original node with children:', originalNode);
                
                // Create a function to recursively create a subtree with inherited attributes
                const createSubtree = (node: TreeNode): TreeNode => {
                  const { baseLabel: nodeBaseLabel, value: nodeValue } = parseNodeLabel(node.label);
                  
                  // Create a composite key for this node
                  const newNodeKey = `${nodeBaseLabel}:${nodeBaseLabel === baseLabel ? (value || '') : (value ? '*' : '')}:${policy.position.toLowerCase()}:${policy.data_access.toLowerCase()}`;
                  
                  console.log(`Creating node with key: ${newNodeKey}`);
                  console.log(`Node exists in map:`, existingNodesMap.has(newNodeKey));
                  
                  // Check if this node already exists
                  if (existingNodesMap.has(newNodeKey)) {
                    console.log(`Node with key ${newNodeKey} already exists, skipping`);
                    return existingNodesMap.get(newNodeKey)!;
                  }
                  
                  const newNode: TreeNode = {
                    label: nodeBaseLabel,
                    // If this is the root node of the subtree, use the policy value
                    // Otherwise, if parent has a specific value, children should have "All Values"
                    value: nodeBaseLabel === baseLabel ? (value || '') : (value ? '*' : ''),
                    children: [],
                    // Always propagate the access and position from the policy to all nodes in the subtree
                    access: policy.data_access.toLowerCase(),
                    position: policy.position.toLowerCase()
                  };
                  
                  // Add the new node to our map
                  existingNodesMap.set(newNodeKey, newNode);
                  console.log(`Added node with key ${newNodeKey} to existingNodesMap`);
                  
                  // Recursively create children with the same access and position
                  if (node.children && node.children.length > 0) {
                    newNode.children = node.children.map(child => createSubtree(child));
                  }
                  
                  return newNode;
                };
                
                // Create the complete subtree
                const newSubtree = createSubtree(originalNode);
                console.log('Created new subtree:', newSubtree);
                
                // Check if the parent already has a child with the same composite key
                const existingChildIndex = updatedParentNode.children.findIndex(child => {
                  const childKey = `${child.label}:${child.value}:${child.position}:${child.access}`;
                  const newKey = `${newSubtree.label}:${newSubtree.value}:${newSubtree.position}:${newSubtree.access}`;
                  return childKey === newKey;
                });
                
                if (existingChildIndex >= 0) {
                  console.log(`Parent already has a child with the same composite key at index ${existingChildIndex}`);
                  console.log('Replacing existing child with new subtree');
                  updatedParentNode.children[existingChildIndex] = newSubtree;
                } else {
                  console.log('Adding new subtree to parent');
                  updatedParentNode.children.push(newSubtree);
                }
                
                // Add all nodes in the subtree to the node map
                const addNodesToNodeMap = (node: TreeNode) => {
                  const nodeKey = `${node.label}:${node.value}:${node.position}:${node.access}`;
                  updatedNodeMap.set(nodeKey, node);
                  
                  if (node.children && node.children.length > 0) {
                    node.children.forEach(addNodesToNodeMap);
                  }
                };
                
                addNodesToNodeMap(newSubtree);
                
                // Mark that changes were made
                changesMade = true;
                
                console.log('Added new subtree to parent and node map');
                console.log('New node map size:', updatedNodeMap.size);
              } else {
                console.log('Original node not found, adding just the new node');
                
                // Check if the parent already has a child with the same composite key
                const existingChildIndex = updatedParentNode.children.findIndex(child => {
                  const childKey = `${child.label}:${child.value}:${child.position}:${child.access}`;
                  const newKey = `${newNode.label}:${newNode.value}:${newNode.position}:${newNode.access}`;
                  return childKey === newKey;
                });
                
                if (existingChildIndex >= 0) {
                  console.log(`Parent already has a child with the same composite key at index ${existingChildIndex}`);
                  console.log('Replacing existing child with new node');
                  updatedParentNode.children[existingChildIndex] = newNode;
                } else {
                  console.log('Adding new node to parent');
                  updatedParentNode.children.push(newNode);
                }
                
                // Add the new node to our map with composite key
                const newNodeKey = `${newNode.label}:${newNode.value}:${newNode.position}:${newNode.access}`;
                updatedNodeMap.set(newNodeKey, newNode);
                existingNodesMap.set(newNodeKey, newNode);
                
                // Mark that changes were made
                changesMade = true;
                
                console.log('Added new node to parent and node map');
                console.log('New node map size:', updatedNodeMap.size);
              }
            } else {
              console.error('Could not find parent node in updated trees');
            }
          } else {
            console.error('Invalid parent tree index:', parentTreeIndex);
          }
        } else {
          console.log(`No suitable parent node found for "${baseLabel}" in the attribute trees`);
          console.log('Creating a new root node for this policy');
          
          // Find the original node in the attribute trees to get its children
          const findOriginalNode = (tree: TreeNode): TreeNode | undefined => {
            const { baseLabel: nodeBaseLabel } = parseNodeLabel(tree.label);
            if (nodeBaseLabel === baseLabel) {
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
          
          // Find the original node to get its children
          let originalNode: TreeNode | undefined;
          for (const tree of attributeTrees) {
            originalNode = findOriginalNode(tree);
            if (originalNode) {
              break;
            }
          }
          
          if (originalNode) {
            console.log('Found original node with children:', originalNode);
            
            // Create a function to recursively create a subtree with inherited attributes
            const createSubtree = (node: TreeNode): TreeNode => {
              const { baseLabel: nodeBaseLabel, value: nodeValue } = parseNodeLabel(node.label);
              
              // Create a composite key for this node
              const newNodeKey = `${nodeBaseLabel}:${nodeBaseLabel === baseLabel ? (value || '') : (value ? '*' : '')}:${policy.position.toLowerCase()}:${policy.data_access.toLowerCase()}`;
              
              console.log(`Creating node with key: ${newNodeKey}`);
              console.log(`Node exists in map:`, existingNodesMap.has(newNodeKey));
              
              // Check if this node already exists
              if (existingNodesMap.has(newNodeKey)) {
                console.log(`Node with key ${newNodeKey} already exists, skipping`);
                return existingNodesMap.get(newNodeKey)!;
              }
              
              const newNode: TreeNode = {
                label: nodeBaseLabel,
                // If this is the root node of the subtree, use the policy value
                // Otherwise, if parent has a specific value, children should have "All Values"
                value: nodeBaseLabel === baseLabel ? (value || '') : (value ? '*' : ''),
                children: [],
                // Always propagate the access and position from the policy to all nodes in the subtree
                access: policy.data_access.toLowerCase(),
                position: policy.position.toLowerCase()
              };
              
              // Add the new node to our map
              existingNodesMap.set(newNodeKey, newNode);
              console.log(`Added node with key ${newNodeKey} to existingNodesMap`);
              
              // Recursively create children with the same access and position
              if (node.children && node.children.length > 0) {
                newNode.children = node.children.map(child => createSubtree(child));
              }
              
              return newNode;
            };
            
            // Create the complete subtree
            const newSubtree = createSubtree(originalNode);
            console.log('Created new subtree for root:', newSubtree);
            
            // Check if a root node with the same composite key already exists
            const existingRootIndex = updatedTrees.findIndex((tree: TreeNode) => {
              const treeKey = `${tree.label}:${tree.value}:${tree.position}:${tree.access}`;
              const newKey = `${newSubtree.label}:${newSubtree.value}:${newSubtree.position}:${newSubtree.access}`;
              return treeKey === newKey;
            });
            
            if (existingRootIndex >= 0) {
              console.log(`Root node with the same composite key already exists at index ${existingRootIndex}`);
              console.log('Replacing existing root with new subtree');
              updatedTrees[existingRootIndex] = newSubtree;
            } else {
              console.log('Adding new subtree as root node');
              updatedTrees.push(newSubtree);
            }
            
            // Add all nodes in the subtree to the node map
            const addNodesToNodeMap = (node: TreeNode) => {
              const nodeKey = `${node.label}:${node.value}:${node.position}:${node.access}`;
              updatedNodeMap.set(nodeKey, node);
              
              if (node.children && node.children.length > 0) {
                node.children.forEach(addNodesToNodeMap);
              }
            };
            
            addNodesToNodeMap(newSubtree);
            
            // Mark that changes were made
            changesMade = true;
            
            console.log('Added new subtree as root and to node map');
            console.log('New node map size:', updatedNodeMap.size);
          } else {
            console.log('Original node not found, creating a new root node');
            
            // Create a new root node
            const newRootNode: TreeNode = {
              label: baseLabel,
              value: value || '', // Use the value from the policy, or empty string if none
              children: [],
              access: policy.data_access.toLowerCase(),
              position: policy.position.toLowerCase()
            };
            
            // Check if a root node with the same composite key already exists
            const existingRootIndex = updatedTrees.findIndex((tree: TreeNode) => {
              const treeKey = `${tree.label}:${tree.value}:${tree.position}:${tree.access}`;
              const newKey = `${newRootNode.label}:${newRootNode.value}:${newRootNode.position}:${newRootNode.access}`;
              return treeKey === newKey;
            });
            
            if (existingRootIndex >= 0) {
              console.log(`Root node with the same composite key already exists at index ${existingRootIndex}`);
              console.log('Replacing existing root with new node');
              updatedTrees[existingRootIndex] = newRootNode;
            } else {
              console.log('Adding new root node to trees');
              updatedTrees.push(newRootNode);
            }
            
            // Add the new root node to our map with composite key
            const newNodeKey = `${newRootNode.label}:${newRootNode.value}:${newRootNode.position}:${newRootNode.access}`;
            updatedNodeMap.set(newNodeKey, newRootNode);
            existingNodesMap.set(newNodeKey, newRootNode);
            
            // Mark that changes were made
            changesMade = true;
            
            console.log('Added new root node to trees and node map');
            console.log('New node map size:', updatedNodeMap.size);
          }
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
        const baseUrl = import.meta.env.PROD 
          ? 'http://localhost:5000' 
          : 'http://localhost:5000';
        
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

  const handleValueChange = (node: TreeNode, value: string) => {
    // Create a deep copy of the trees to avoid mutating state directly
    const updatedTrees = JSON.parse(JSON.stringify(attributeTrees));
    
    // Function to update the node in the tree
    const updateNode = (trees: TreeNode[]): boolean => {
      for (let i = 0; i < trees.length; i++) {
        if (trees[i] === node) {
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
    setAttributeTrees(updatedTrees);
    
    // Here you would typically send the updated trees to the backend
    console.log('Value updated:', node.label, value);
  };

  const addCalendarWeekPolicy = () => {
    // First, add the policy to the backend
    const apiUrl = import.meta.env.PROD 
      ? 'http://localhost:5000/add_policy' 
      : 'http://localhost:5000/add_policy'; // Always use the full URL for now
    
    console.log('Adding policy to:', apiUrl);
    
    const policyData = {
      granular_data: "Calendar:Week(67th)",
      data_access: "Write",
      position: "Next"
    };
    
    console.log('Policy data being sent:', policyData);
    console.log('Current attribute trees:', attributeTrees);
    
    fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(policyData),
    })
    .then(response => {
      console.log('Response status:', response.status);
      console.log('Response headers:', response.headers);
      
      if (!response.ok) {
        return response.text().then(text => {
          console.error('Error response text:', text);
          throw new Error(`Failed to add policy: ${response.status} ${response.statusText}`);
        });
      }
      return response.json();
    })
    .then(data => {
      console.log('Policy added successfully:', data);
      
      // Fetch updated data after adding policy
      console.log('Fetching updated data after adding policy');
      const baseUrl = import.meta.env.PROD 
        ? 'http://localhost:5000' 
        : 'http://localhost:5000';
      
      // Fetch updated attribute trees and policies
      Promise.all([
        fetch(`${baseUrl}/get_attribute_trees`).then(res => res.json()),
        fetch(`${baseUrl}/get_policies`).then(res => res.json())
      ])
      .then(([treesData, policiesData]) => {
        console.log('Received updated attribute trees:', treesData);
        console.log('Received updated policies:', policiesData);
        
        // Update state with new data
        setAttributeTrees(treesData.attribute_trees || []);
        setPolicies(policiesData.policies || []);
        
        // Apply policies after updating state
        console.log('Applying policies after updating state');
        setTimeout(() => {
          applyPolicies();
        }, 100);
      })
      .catch(err => {
        console.error('Error fetching updated data:', err);
        setError(err instanceof Error ? err.message : String(err));
      });
    })
    .catch(err => {
      console.error('Error adding policy:', err);
      setError(err instanceof Error ? err.message : String(err));
    });
  };

  const addCalendarDayPolicy = () => {
    // First, add the policy to the backend
    const apiUrl = import.meta.env.PROD 
      ? 'http://localhost:5000/add_policy' 
      : 'http://localhost:5000/add_policy';
    
    console.log('Adding Calendar:Day policy to:', apiUrl);
    
    const policyData = {
      granular_data: "Calendar:Day(Monday)",
      data_access: "Read",
      position: "Previous"
    };
    
    console.log('Policy data being sent:', policyData);
    
    fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(policyData),
    })
    .then(response => {
      if (!response.ok) {
        return response.text().then(text => {
          console.error('Error response text:', text);
          throw new Error(`Failed to add policy: ${response.status} ${response.statusText}`);
        });
      }
      return response.json();
    })
    .then(data => {
      console.log('Calendar:Day policy added successfully:', data);
      
      // Fetch updated data after adding policy
      const baseUrl = import.meta.env.PROD 
        ? 'http://localhost:5000' 
        : 'http://localhost:5000';
      
      // Fetch updated attribute trees and policies
      Promise.all([
        fetch(`${baseUrl}/get_attribute_trees`).then(res => res.json()),
        fetch(`${baseUrl}/get_policies`).then(res => res.json())
      ])
      .then(([treesData, policiesData]) => {
        // Update state with new data
        setAttributeTrees(treesData.attribute_trees || []);
        setPolicies(policiesData.policies || []);
        
        // Apply policies after updating state
        setTimeout(() => {
          applyPolicies();
        }, 100);
      })
      .catch(err => {
        console.error('Error fetching updated data:', err);
        setError(err instanceof Error ? err.message : String(err));
      });
    })
    .catch(err => {
      console.error('Error adding Calendar:Day policy:', err);
      setError(err instanceof Error ? err.message : String(err));
    });
  };

  const addExpediaExperiencePolicy = () => {
    // First, add the policy to the backend
    const apiUrl = import.meta.env.PROD 
      ? 'http://localhost:5000/add_policy' 
      : 'http://localhost:5000/add_policy';
    
    console.log('Adding Expedia:Experience policy to:', apiUrl);
    
    const policyData = {
      granular_data: "Expedia:Experience(*)",
      data_access: "Write",
      position: "Current"
    };
    
    console.log('Policy data being sent:', policyData);
    
    fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(policyData),
    })
    .then(response => {
      if (!response.ok) {
        return response.text().then(text => {
          console.error('Error response text:', text);
          throw new Error(`Failed to add policy: ${response.status} ${response.statusText}`);
        });
      }
      return response.json();
    })
    .then(data => {
      console.log('Expedia:Experience policy added successfully:', data);
      
      // Fetch updated data after adding policy
      const baseUrl = import.meta.env.PROD 
        ? 'http://localhost:5000' 
        : 'http://localhost:5000';
      
      // Fetch updated attribute trees and policies
      Promise.all([
        fetch(`${baseUrl}/get_attribute_trees`).then(res => res.json()),
        fetch(`${baseUrl}/get_policies`).then(res => res.json())
      ])
      .then(([treesData, policiesData]) => {
        // Update state with new data
        setAttributeTrees(treesData.attribute_trees || []);
        setPolicies(policiesData.policies || []);
        
        // Apply policies after updating state
        setTimeout(() => {
          applyPolicies();
        }, 100);
      })
      .catch(err => {
        console.error('Error fetching updated data:', err);
        setError(err instanceof Error ? err.message : String(err));
      });
    })
    .catch(err => {
      console.error('Error adding Expedia:Experience policy:', err);
      setError(err instanceof Error ? err.message : String(err));
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

    // If we're in 'permitted' view, only show nodes with permissions
    if (viewMode === 'permitted') {
      // If this node has access or position set, keep it
      if (node.access || node.position) {
        // Create a new node with filtered children
        const filteredNode: TreeNode = {
          ...node,
          children: []
        };

        // Recursively filter children
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

      // If this node doesn't have access or position set, but has children that do
      if (node.children && node.children.length > 0) {
        const filteredChildren: TreeNode[] = [];
        
        node.children.forEach(child => {
          const filteredChild = filterNodes(child);
          if (filteredChild) {
            filteredChildren.push(filteredChild);
          }
        });

        // If any children passed the filter, return them directly
        if (filteredChildren.length > 0) {
          // Return all filtered children as separate root nodes
          return filteredChildren[0];
        }
      }

      return null;
    }

    // If we're in 'edit' view, only show nodes with default values
    if (viewMode === 'edit') {
      // If this node has no access or position set, keep it
      if (!node.access && !node.position) {
        // Create a new node with filtered children
        const filteredNode: TreeNode = {
          ...node,
          children: []
        };

        // Recursively filter children
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

      return null;
    }

    return node;
  };

  // Function to get all permission nodes with their complete subtrees
  const getAllPermissionNodes = (trees: TreeNode[]): TreeNode[] => {
    const permissionNodes: TreeNode[] = [];
    
    const traverse = (node: TreeNode) => {
      // If this node has a non-default value, add it and its children as a root
      if (node.value !== '' && node.value !== 'default') {
        const permissionNode: TreeNode = {
          ...node,
          children: []
        };
        
        // Add all children as they are
        if (node.children && node.children.length > 0) {
          node.children.forEach(child => {
            const childCopy = {
              ...child,
              children: []
            };
            permissionNode.children.push(childCopy);
          });
        }
        
        permissionNodes.push(permissionNode);
        return; // Don't traverse children of this node
      }
      
      // If this node has default value, traverse its children
      if (node.children && node.children.length > 0) {
        node.children.forEach(traverse);
      }
    };
    
    // Traverse all trees
    trees.forEach(traverse);
    
    return permissionNodes;
  };

  // Function to handle policy deletion
  const handleDeletePolicy = async (policyData: any) => {
    try {
      setIsLoading(true);
      
      // Send delete request to backend
      const apiUrl = import.meta.env.PROD 
        ? 'http://localhost:5000/delete_policy' 
        : 'http://localhost:5000/delete_policy';
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(policyData),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to delete policy: ${response.status} ${response.statusText}`);
      }

      // Fetch updated data after deleting policy
      const baseUrl = import.meta.env.PROD 
        ? 'http://localhost:5000' 
        : 'http://localhost:5000';
      
      // Fetch updated attribute trees and policies
      const [treesData, policiesData] = await Promise.all([
        fetch(`${baseUrl}/get_attribute_trees`).then(res => res.json()),
        fetch(`${baseUrl}/get_policies`).then(res => res.json())
      ]);

      // Update state with new data
      setAttributeTrees(treesData.attribute_trees || []);
      setPolicies(policiesData.policies || []);
      
      // Apply policies after updating state
      setTimeout(() => {
        applyPolicies();
      }, 100);
    } catch (err) {
      console.error('Error deleting policy:', err);
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
      />
    </Box>
  );

  return (
    <div className={styles.chatContainer}>
      <Box className={styles.messagesContainer} overflow="auto">
        <HStack justify="space-between" mb={4}>
          <Text fontSize="lg" fontWeight="bold">
            Permission Attribute Trees
          </Text>
          <HStack spacing={2}>
            <Button 
              size="sm" 
              colorScheme="blue" 
              onClick={addCalendarWeekPolicy}
            >
              Add Calendar:Week Policy
            </Button>
            <Button 
              size="sm" 
              colorScheme="green" 
              onClick={addCalendarDayPolicy}
            >
              Add Calendar:Day Policy
            </Button>
            <Button 
              size="sm" 
              colorScheme="purple" 
              onClick={addExpediaExperiencePolicy}
            >
              Add Expedia:Experience Policy
            </Button>
            <Button 
              size="sm" 
              colorScheme="teal" 
              onClick={requestPolicyUpdate}
            >
              Refresh Trees
            </Button>
          </HStack>
        </HStack>

        <HStack mb={4} justify="center" spacing={4}>
          <Button
            size="md"
            colorScheme={viewMode === 'all' ? 'blue' : 'gray'}
            onClick={() => setViewMode('all')}
          >
            All Attributes
          </Button>
          <Button
            size="md"
            colorScheme={viewMode === 'permitted' ? 'blue' : 'gray'}
            onClick={() => setViewMode('permitted')}
          >
            All Permissions
          </Button>
          <Button
            size="md"
            colorScheme={viewMode === 'edit' ? 'blue' : 'gray'}
            onClick={() => setViewMode('edit')}
          >
            Edit View
          </Button>
        </HStack>
        
        {isLoading && (
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
        
        {!isLoading && !error && attributeTrees.length === 0 && (
          <Box p={3} borderRadius="md" bg="gray.50">
            <Text>No attribute trees available yet.</Text>
          </Box>
        )}
        
        {!isLoading && !error && attributeTrees.length > 0 && (
          <VStack align="stretch" spacing={2} width="100%">
            {viewMode === 'permitted' 
              ? getAllPermissionNodes(attributeTrees).map((tree, index) => renderTree(tree, index))
              : attributeTrees.map((tree, index) => {
                  const filteredTree = filterNodes(tree);
                  return filteredTree ? renderTree(filteredTree, index) : null;
                })
            }
          </VStack>
        )}
      </Box>
    </div>
  );
};

export default PermissionChat; 