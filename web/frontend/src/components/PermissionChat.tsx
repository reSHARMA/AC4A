import { useState, useEffect } from 'react'
import React from 'react'
import { Box, Text, VStack, Spinner, Select, HStack, Badge, Button, Switch } from '@chakra-ui/react'
import { FaFolder, FaFolderOpen, FaFile } from 'react-icons/fa'
import styles from './Chat.module.css'
import { io, Socket } from 'socket.io-client'

interface TreeNode {
  label: string;
  value: string;
  children: TreeNode[];
  access?: string;
  position?: string;
}

interface Policy {
  granular_data: string;
  data_access: string;
  position: string;
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
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [socket, setSocket] = useState<Socket | null>(null);
  const [nodeMap, setNodeMap] = useState<Map<string, TreeNode>>(new Map());
  const [showOnlyPermittedNodes, setShowOnlyPermittedNodes] = useState(false);

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
      setLoading(false);
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
        // Create a composite key using all attributes
        const nodeKey = `${node.label}:${node.value || '*'}:${node.access || ''}:${node.position || ''}`;
        // Map the composite key to the full node data
        newNodeMap.set(nodeKey, {
          ...node,
          value: node.value || node.label,
          access: node.access || '',
          position: node.position || ''
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
      
      // Create composite key for node lookup using all attributes
      const nodeKey = `${policy.granular_data}:${policy.granular_data}:${policy.data_access.toLowerCase()}:${policy.position.toLowerCase()}`;
      
      // Check if a node with these exact attributes exists in our map
      const existingNode = updatedNodeMap.get(nodeKey);
      
      if (existingNode) {
        console.log('Found existing node with same attributes:', existingNode);
        return; // Node already exists with these exact attributes
      } else {
        console.log('Node not found with these attributes, creating new node:', policy.granular_data);
        
        // Find the parent node by searching through the existing attribute trees
        let parentNode: TreeNode | undefined;
        let parentTreeIndex = -1;
        
        // Helper function to search through a tree
        const findParentInTree = (tree: TreeNode, treeIndex: number): TreeNode | undefined => {
          console.log(`Searching in tree node: ${tree.label}`);
          console.log(`Looking for parent of node with label: ${policy.granular_data}`);
          console.log(`Current node's children:`, tree.children.map(child => child.label));
          
          // Check if any of this node's children match the policy's granular_data by label only
          const matchingChild = tree.children.find(child => child.label === policy.granular_data);
          
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
            label: policy.granular_data,
            value: policy.granular_data,
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
                if (tree.label === policy.granular_data) {
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
                  const newNode: TreeNode = {
                    label: node.label,
                    value: node.value,
                    children: [],
                    access: policy.data_access.toLowerCase(),
                    position: policy.position.toLowerCase()
                  };
                  
                  // Recursively create children
                  if (node.children && node.children.length > 0) {
                    newNode.children = node.children.map(child => createSubtree(child));
                  }
                  
                  return newNode;
                };
                
                // Create the complete subtree
                const newSubtree = createSubtree(originalNode);
                console.log('Created new subtree:', newSubtree);
                
                // Add the new subtree to the parent
                updatedParentNode.children.push(newSubtree);
                
                // Add all nodes in the subtree to the node map
                const addNodesToMap = (node: TreeNode) => {
                  const nodeKey = `${node.label}:${node.value}:${node.position}:${node.access}`;
                  updatedNodeMap.set(nodeKey, node);
                  
                  if (node.children && node.children.length > 0) {
                    node.children.forEach(addNodesToMap);
                  }
                };
                
                addNodesToMap(newSubtree);
                
                // Mark that changes were made
                changesMade = true;
                
                console.log('Added new subtree to parent and node map');
                console.log('New node map size:', updatedNodeMap.size);
              } else {
                console.log('Original node not found, adding just the new node');
                
                // Add just the new node if the original node is not found
                updatedParentNode.children.push(newNode);
                
                // Add the new node to our map with composite key
                const newNodeKey = `${newNode.label}:${newNode.value}:${newNode.position}:${newNode.access}`;
                updatedNodeMap.set(newNodeKey, newNode);
                
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
          console.log(`No suitable parent node found for "${policy.granular_data}" in the attribute trees`);
          console.log('Creating a new root node for this policy');
          
          // Find the original node in the attribute trees to get its children
          const findOriginalNode = (tree: TreeNode): TreeNode | undefined => {
            if (tree.label === policy.granular_data) {
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
              const newNode: TreeNode = {
                label: node.label,
                value: node.value,
                children: [],
                access: policy.data_access.toLowerCase(),
                position: policy.position.toLowerCase()
              };
              
              // Recursively create children
              if (node.children && node.children.length > 0) {
                newNode.children = node.children.map(child => createSubtree(child));
              }
              
              return newNode;
            };
            
            // Create the complete subtree
            const newSubtree = createSubtree(originalNode);
            console.log('Created new subtree for root:', newSubtree);
            
            // Add the new subtree as a root node
            updatedTrees.push(newSubtree);
            
            // Add all nodes in the subtree to the node map
            const addNodesToMap = (node: TreeNode) => {
              const nodeKey = `${node.label}:${node.value}:${node.position}:${node.access}`;
              updatedNodeMap.set(nodeKey, node);
              
              if (node.children && node.children.length > 0) {
                node.children.forEach(addNodesToMap);
              }
            };
            
            addNodesToMap(newSubtree);
            
            // Mark that changes were made
            changesMade = true;
            
            console.log('Added new subtree as root and to node map');
            console.log('New node map size:', updatedNodeMap.size);
          } else {
            console.log('Original node not found, creating a new root node');
            
            // Create a new root node
            const newRootNode: TreeNode = {
              label: policy.granular_data,
              value: policy.granular_data,
              children: [],
              access: policy.data_access.toLowerCase(),
              position: policy.position.toLowerCase()
            };
            
            // Add the new root node to the trees
            updatedTrees.push(newRootNode);
            
            // Add the new root node to our map with composite key
            const newNodeKey = `${newRootNode.label}:${newRootNode.value}:${newRootNode.position}:${newRootNode.access}`;
            updatedNodeMap.set(newNodeKey, newRootNode);
            
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
        setLoading(true);
        
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
        setLoading(false);
        
        // Apply policies after fetching data
        console.log('Applying policies after fetching data');
        setTimeout(() => {
          applyPolicies();
        }, 100);
      } catch (err) {
        console.error('Error fetching data:', err);
        setError(err instanceof Error ? err.message : String(err));
        setLoading(false);
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

  const addCalendarWeekPolicy = () => {
    // First, add the policy to the backend
    const apiUrl = import.meta.env.PROD 
      ? 'http://localhost:5000/add_policy' 
      : 'http://localhost:5000/add_policy'; // Always use the full URL for now
    
    console.log('Adding policy to:', apiUrl);
    
    const policyData = {
      granular_data: "Calendar:Week",
      data_access: "Read",
      position: "Current"
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
      granular_data: "Calendar:Day",
      data_access: "Write",
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
      granular_data: "Expedia:Experience",
      data_access: "Read",
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

  // Function to filter nodes based on the toggle state
  const filterNodes = (node: TreeNode): TreeNode | null => {
    // If we're not filtering, return the node as is
    if (!showOnlyPermittedNodes) {
      return node;
    }

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
        // If there's only one child, return it directly
        if (filteredChildren.length === 1) {
          return filteredChildren[0];
        }
        
        // If there are multiple children, create a new node with these children
        // but don't include the original node's label/value
        return {
          label: "Filtered Nodes",
          value: "Filtered Nodes",
          children: filteredChildren,
          access: "",
          position: ""
        };
      }
    }

    // If this node has no access/position and no children with access/position, filter it out
    return null;
  };

  // Function to extract all nodes with permissions from the trees
  const extractPermittedNodes = (trees: TreeNode[]): TreeNode[] => {
    const permittedNodes: TreeNode[] = [];
    
    const extractFromNode = (node: TreeNode) => {
      // If this node has access or position set, add it to the permitted nodes
      if (node.access || node.position) {
        permittedNodes.push({...node});
      }
      
      // Recursively process children
      if (node.children && node.children.length > 0) {
        node.children.forEach(child => {
          extractFromNode(child);
        });
      }
    };
    
    // Process each tree
    trees.forEach(tree => {
      extractFromNode(tree);
    });
    
    return permittedNodes;
  };

  // Function to promote nodes with values up one level
  const promoteNodesWithValues = (node: TreeNode): TreeNode | null => {
    // If we're not filtering, return the node as is
    if (!showOnlyPermittedNodes) {
      return node;
    }

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
          const filteredChild = promoteNodesWithValues(child);
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
        const filteredChild = promoteNodesWithValues(child);
        if (filteredChild) {
          filteredChildren.push(filteredChild);
        }
      });

      // If any children passed the filter, return them directly
      if (filteredChildren.length > 0) {
        // If there's only one child, return it directly
        if (filteredChildren.length === 1) {
          return filteredChildren[0];
        }
        
        // If there are multiple children, return them as an array
        // This will be handled by the rendering logic
        return {
          label: "Multiple Roots",
          value: "Multiple Roots",
          children: filteredChildren,
          access: "",
          position: ""
        };
      }
    }

    // If this node has no access/position and no children with access/position, filter it out
    return null;
  };

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

        <HStack mb={4} justify="flex-end">
          <Text fontSize="sm">Show only nodes with permissions:</Text>
          <Switch 
            isChecked={showOnlyPermittedNodes} 
            onChange={(e) => setShowOnlyPermittedNodes(e.target.checked)}
            colorScheme="blue"
          />
        </HStack>
        
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
            {attributeTrees.map((tree, index) => {
              // Apply filtering if needed
              const filteredTree = promoteNodesWithValues(tree);
              
              // Only render if the tree has nodes after filtering
              if (filteredTree) {
                // Check if this is a "Multiple Roots" node
                if (filteredTree.label === "Multiple Roots") {
                  // Render each child as a separate root
                  return (
                    <React.Fragment key={index}>
                      {filteredTree.children.map((child, childIndex) => (
                        <Box key={`${index}-${childIndex}`} p={2} borderRadius="md" bg="white" boxShadow="sm">
                          <TreeView 
                            data={child} 
                            isRoot={true} 
                            onAccessChange={handleAccessChange}
                            onPositionChange={handlePositionChange}
                          />
                        </Box>
                      ))}
                    </React.Fragment>
                  );
                }
                
                // Normal case - render the filtered tree
                return (
                  <Box key={index} p={2} borderRadius="md" bg="white" boxShadow="sm">
                    <TreeView 
                      data={filteredTree} 
                      isRoot={true} 
                      onAccessChange={handleAccessChange}
                      onPositionChange={handlePositionChange}
                    />
                  </Box>
                );
              }
              return null;
            })}
          </VStack>
        )}
      </Box>
    </div>
  );
};

export default PermissionChat; 