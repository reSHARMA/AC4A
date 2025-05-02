import React, { useState, useEffect, useRef } from 'react';
import { Box, VStack, HStack, Text, Select, Input, Button, useToast, InputGroup, InputLeftElement } from '@chakra-ui/react';
import { SearchIcon } from '@chakra-ui/icons';
import { socket } from '../socket';

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  source: string;
}

const LogsView: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<LogEntry[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [levelFilter, setLevelFilter] = useState('all');
  const [sourceFilter, setSourceFilter] = useState('all');
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
        setLogs([]);
        setFilteredLogs([]);
        // Also fetch fresh logs after reset
        fetchLogs();
      }
    };

    const handleNewLog = (newLog: LogEntry) => {
      console.log('New log received:', newLog);
      setLogs(prevLogs => {
        const updatedLogs = [...prevLogs, newLog];
        // Apply current filters to the new log
        let filtered = updatedLogs;
        if (levelFilter !== 'all') {
          filtered = filtered.filter(log => log.level.toLowerCase() === levelFilter.toLowerCase());
        }
        if (sourceFilter !== 'all') {
          filtered = filtered.filter(log => log.source.toLowerCase() === sourceFilter.toLowerCase());
        }
        if (searchTerm) {
          const term = searchTerm.toLowerCase();
          filtered = filtered.filter(log => 
            log.message.toLowerCase().includes(term) ||
            log.timestamp.toLowerCase().includes(term)
          );
        }
        setFilteredLogs(filtered);
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

    // Initial fetch
    fetchLogs();

    // Clean up
    return () => {
      console.log('Cleaning up socket event listeners');
      socket.off('connect', handleConnect);
      socket.off('disconnect', handleDisconnect);
      socket.off('session_reset', handleSessionReset);
      socket.off('new_log', handleNewLog);
    };
  }, [levelFilter, sourceFilter, searchTerm]);

  // Fetch logs from backend
  const fetchLogs = async () => {
    try {
      setIsLoading(true);
      console.log('Fetching logs from /get_logs');
      const response = await fetch('/get_logs');
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        throw new Error(`Failed to fetch logs: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Received logs:', data.logs.length);
      setLogs(data.logs);
      setFilteredLogs(data.logs);
    } catch (error) {
      console.error('Error in fetchLogs:', error);
      toast({
        title: 'Error fetching logs',
        description: error instanceof Error ? error.message : 'Unknown error occurred',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Get unique log levels and sources for filters
  const logLevels = ['all', ...new Set(logs.map(log => log.level.toLowerCase()))];
  const logSources = ['all', ...new Set(logs.map(log => log.source.toLowerCase()))];

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
                {level.charAt(0).toUpperCase() + level.slice(1)}
              </option>
            ))}
          </Select>
          <Select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            width="120px"
            size="sm"
          >
            {logSources.map(source => (
              <option key={source} value={source}>
                {source.charAt(0).toUpperCase() + source.slice(1)}
              </option>
            ))}
          </Select>
          <Button
            leftIcon={<SearchIcon boxSize={3} />}
            onClick={fetchLogs}
            isLoading={isLoading}
            size="sm"
          >
            Refresh
          </Button>
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
                    <Text fontSize="xs" color="gray.500" minW="140px">
                      {log.timestamp}
                    </Text>
                    <Text
                      fontSize="xs"
                      fontWeight="bold"
                      color={
                        log.level.toLowerCase() === 'error'
                          ? 'red.500'
                          : log.level.toLowerCase() === 'warning'
                          ? 'yellow.500'
                          : 'blue.500'
                      }
                      minW="60px"
                    >
                      {log.level}
                    </Text>
                    <Text fontSize="xs" color="gray.500" minW="100px">
                      {log.source}
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