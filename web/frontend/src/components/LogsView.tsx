import React, { useState, useEffect, useRef } from 'react';
import { Box, VStack, HStack, Text, Select, Input, Button, useToast, InputGroup, InputLeftElement } from '@chakra-ui/react';
import { SearchIcon } from '@chakra-ui/icons';
import { socket } from '../socket';

interface LogEntry {
  level: string;
  message: string;
}

// Create a persistent store for logs outside the component
const logStore = {
  logs: [] as LogEntry[],
  filteredLogs: [] as LogEntry[],
  setLogs: (newLogs: LogEntry[]) => {
    logStore.logs = newLogs;
  },
  setFilteredLogs: (newFilteredLogs: LogEntry[]) => {
    logStore.filteredLogs = newFilteredLogs;
  }
};

const LogsView: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>(logStore.logs);
  const [filteredLogs, setFilteredLogs] = useState<LogEntry[]>(logStore.filteredLogs);
  const [searchTerm, setSearchTerm] = useState('');
  const [levelFilter, setLevelFilter] = useState('all');
  const [isLoading, setIsLoading] = useState(false);
  const toast = useToast();
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when new logs arrive
  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [filteredLogs]);

  // Set up socket event listeners
  useEffect(() => {
    console.log('Setting up socket event listeners');

    const handleConnect = () => {
      console.log('Socket connected');
    };

    const handleDisconnect = () => {
      console.log('Socket disconnected');
    };

    const handleSessionReset = (data: { reset: boolean }) => {
      console.log('Session reset event received with data:', data);
      if (data.reset) {
        const emptyLogs: LogEntry[] = [];
        setLogs(emptyLogs);
        setFilteredLogs(emptyLogs);
        logStore.setLogs(emptyLogs);
        logStore.setFilteredLogs(emptyLogs);
        // Also fetch fresh logs after reset
        fetchLogs();
      }
    };

    const handleNewLog = (newLog: LogEntry) => {
      console.log('New log received:', newLog);
      setLogs(prevLogs => {
        const updatedLogs = [...prevLogs, newLog];
        logStore.setLogs(updatedLogs);
        return updatedLogs;
      });
    };

    // Connect socket if not already connected
    if (!socket.connected) {
      console.log('Socket not connected, connecting...');
      socket.connect();
    }

    // Set up event listeners
    socket.on('connect', handleConnect);
    socket.on('disconnect', handleDisconnect);
    socket.on('session_reset', handleSessionReset);
    socket.on('new_log', handleNewLog);

    // Initial fetch if we don't have logs yet
    if (logs.length === 0) {
      fetchLogs();
    }

    // Clean up
    return () => {
      console.log('Cleaning up socket event listeners');
      socket.off('connect', handleConnect);
      socket.off('disconnect', handleDisconnect);
      socket.off('session_reset', handleSessionReset);
      socket.off('new_log', handleNewLog);
    };
  }, []);

  // Separate effect for handling filter changes
  useEffect(() => {
    const filtered = logs.filter(log => {
      if (levelFilter !== 'all' && String(log.level) !== levelFilter) {
        return false;
      }
      if (searchTerm && !log.message.toLowerCase().includes(searchTerm.toLowerCase())) {
        return false;
      }
      return true;
    });
    setFilteredLogs(filtered);
    logStore.setFilteredLogs(filtered);
  }, [logs, levelFilter, searchTerm]);

  // Fetch logs from backend
  const fetchLogs = async () => {
    try {
      setIsLoading(true);
      console.log('Fetching logs...');
      const response = await fetch('/get_logs');
      console.log('Logs response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response text:', errorText);
        throw new Error(`Failed to fetch logs: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Received logs:', data.logs.length);
      
      setLogs(data.logs);
      logStore.setLogs(data.logs);
      
      // Apply filters to the logs
      const filteredLogs = data.logs.filter((log: LogEntry) => {
        if (levelFilter !== 'all' && String(log.level) !== levelFilter) {
          return false;
        }
        if (searchTerm && !log.message.toLowerCase().includes(searchTerm.toLowerCase())) {
          return false;
        }
        return true;
      });
      
      setFilteredLogs(filteredLogs);
      logStore.setFilteredLogs(filteredLogs);
    } catch (error) {
      console.error('Error fetching logs:', error);
      toast({
        title: 'Error fetching logs',
        description: error instanceof Error ? error.message : 'Unknown error',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Get unique log levels for filters
  const logLevels = ['all', ...new Set(logs.map(log => String(log.level)))].sort((a, b) => {
    if (a === 'all') return -1;
    if (b === 'all') return 1;
    return Number(a) - Number(b);
  });

  return (
    <Box p={4} maxW="800px" mx="auto">
      <VStack spacing={4} align="stretch">
        {/* Filters */}
        <HStack spacing={2}>
          <InputGroup size="sm" maxW="200px">
            <InputLeftElement pointerEvents="none">
              <SearchIcon color="gray.500" boxSize={3} />
            </InputLeftElement>
            <Input
              placeholder="Search logs..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              size="sm"
            />
          </InputGroup>
          <Select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            width="120px"
            size="sm"
          >
            {logLevels.map(level => (
              <option key={level} value={level}>
                {level === 'all' ? 'All Categories' : `Category ${level}`}
              </option>
            ))}
          </Select>
        </HStack>

        {/* Logs display */}
        <Box
          height="500px"
          overflowY="auto"
          bg="gray.50"
          borderRadius="md"
          p={2}
          fontSize="sm"
        >
          {filteredLogs.length === 0 ? (
            <Text textAlign="center" color="gray.500">
              No logs found
            </Text>
          ) : (
            <VStack spacing={1} align="stretch">
              {filteredLogs.map((log, index) => (
                <Box
                  key={index}
                  p={1}
                  bg="white"
                  borderRadius="md"
                  boxShadow="sm"
                >
                  <HStack spacing={2}>
                    <Text
                      fontSize="xs"
                      fontWeight="bold"
                      color="blue.500"
                      minW="60px"
                    >
                      [{log.level}]
                    </Text>
                    <Text fontSize="xs" isTruncated>{log.message}</Text>
                  </HStack>
                </Box>
              ))}
              <div ref={logsEndRef} />
            </VStack>
          )}
        </Box>
      </VStack>
    </Box>
  );
};

export default LogsView; 