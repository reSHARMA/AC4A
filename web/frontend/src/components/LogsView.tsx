import React, { useState, useEffect, useRef } from 'react';
import { Box, VStack, HStack, Text, Select, Input, Button, useToast, InputGroup, InputLeftElement } from '@chakra-ui/react';
import { SearchIcon } from '@chakra-ui/icons';
import { socket } from '../socket';

interface LogEntry {
  level: string;
  message: string;
  source?: string;
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
  },
  // Add a function to add a single log
  addLog: (log: LogEntry) => {
    // Don't strip the CUSTOM_ prefix here, just add the log as is
    logStore.logs = [...logStore.logs, log];
    return logStore.logs;
  }
};

const LogsView: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>(logStore.logs);
  const [filteredLogs, setFilteredLogs] = useState<LogEntry[]>(logStore.filteredLogs);
  const [searchTerm, setSearchTerm] = useState('');
  const [levelFilter, setLevelFilter] = useState('all');
  const toast = useToast();
  const logsEndRef = useRef<HTMLDivElement>(null);
  const [isMounted, setIsMounted] = useState(false);

  // Scroll to bottom when new logs arrive
  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [filteredLogs]);

  // On mount: fetch initial logs to backfill any missed events
  useEffect(() => {
    const port = import.meta.env.VITE_PORT || '5002';
    const baseUrl = import.meta.env.PROD ? `http://localhost:${port}` : `http://localhost:${port}`;
    fetch(`${baseUrl}/get_logs`)
      .then(res => res.json())
      .then(data => {
        console.log('Fetched initial logs:', data.logs);
        const initialLogs: LogEntry[] = (data.logs || []).map((log: any) => {
          const rawLevel = log.level || '';
          const level = rawLevel.startsWith('CUSTOM_') ? rawLevel.slice(7) : rawLevel;
          return {
            level,
            message: log.message,
            source: log.source
          };
        });
        logStore.setLogs(initialLogs);
        setLogs(initialLogs);
        setFilteredLogs(initialLogs);
        logStore.setFilteredLogs(initialLogs);
      })
      .catch(err => console.error('Error fetching initial logs:', err));
  }, []);

  // Set up socket event listeners
  useEffect(() => {
    console.log('Setting up socket event listeners');
    console.log('Socket connection status:', socket.connected);
    console.log('Socket ID:', socket.id);

    const handleConnect = () => {
      console.log('Socket connected');
      console.log('Socket connection status:', socket.connected);
      console.log('Socket ID:', socket.id);
    };

    const handleDisconnect = () => {
      console.log('Socket disconnected');
      console.log('Socket connection status:', socket.connected);
      console.log('Socket ID:', socket.id);
    };

    const handleSessionReset = (data: { reset: boolean }) => {
      console.log('Session reset event received with data:', data);
      if (data.reset) {
        const emptyLogs: LogEntry[] = [];
        setLogs(emptyLogs);
        setFilteredLogs(emptyLogs);
        logStore.setLogs(emptyLogs);
        logStore.setFilteredLogs(emptyLogs);
      }
    };

    const handleNewLog = (newLog: LogEntry) => {
      console.log('New log received:', newLog);
      console.log('Socket connection status:', socket.connected);
      console.log('Socket ID:', socket.id);
      // Strip the CUSTOM_ prefix from the level before displaying
      const rawLevel = newLog.level || '';
      const level = rawLevel.startsWith('CUSTOM_') ? rawLevel.slice(7) : rawLevel;
      const logEntry: LogEntry = {
        level,
        message: newLog.message,
        source: newLog.source
      };
      console.log('Processed log entry:', logEntry);
      // Use the store's addLog function to ensure consistency
      const updatedLogs = logStore.addLog(logEntry);
      console.log('Updated logs:', updatedLogs);
      setLogs(updatedLogs);
      // Update filtered logs immediately
      const filtered = updatedLogs.filter(log => {
        const matchesLevel = levelFilter === 'all' || String(log.level) === levelFilter;
        const matchesSearch = !searchTerm || log.message.toLowerCase().includes(searchTerm.toLowerCase());
        console.log(`Log filtering - level: ${log.level}, matchesLevel: ${matchesLevel}, matchesSearch: ${matchesSearch}`);
        return matchesLevel && matchesSearch;
      });
      console.log('Filtered logs:', filtered);
      setFilteredLogs(filtered);
    };

    // Connect socket if not already connected
    if (!socket.connected) {
      console.log('Socket not connected, connecting...');
      socket.connect();
    } else {
      console.log('Socket already connected');
    }

    // Set up event listeners
    console.log('Setting up socket event listeners');
    socket.on('connect', handleConnect);
    socket.on('disconnect', handleDisconnect);
    socket.on('session_reset', handleSessionReset);
    socket.on('new_log', handleNewLog);

    // Mark component as mounted
    setIsMounted(true);
    console.log('LogsView component mounted');

    // Clean up
    return () => {
      console.log('Cleaning up socket event listeners');
      socket.off('connect', handleConnect);
      socket.off('disconnect', handleDisconnect);
      socket.off('session_reset', handleSessionReset);
      socket.off('new_log', handleNewLog);
      setIsMounted(false);
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

  // Get unique log levels for filters
  const logLevels = ['all', ...new Set(logs.map(log => String(log.level)))]
    .filter(level => level !== 'CUSTOM_') // Filter out CUSTOM_ prefix
    .sort((a, b) => {
      if (a === 'all') return -1;
      if (b === 'all') return 1;
      return Number(a) - Number(b);
    });

  return (
    <Box p={4} width="100%">
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
            width="200px"
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
          p={4}
          fontSize="sm"
          boxShadow="sm"
        >
          {filteredLogs.length === 0 ? (
            <Text textAlign="center" color="gray.500">
              No logs found
            </Text>
          ) : (
            <VStack spacing={2} align="stretch">
              {filteredLogs.map((log, index) => {
                // Define colors for different log categories
                const getCategoryColor = (level: string) => {
                  if (level === 'Permission Added') return 'green.500';
                  if (level === 'Permission Removed') return 'red.500';
                  if (level === 'Calling') return 'blue.500';
                  if (level.startsWith('❌ Access') && level.includes('Denied')) return 'red.500';
                  if (level === '✅ Access Granted by') return 'green.500';
                  return 'gray.500';
                };

                return (
                  <Box
                    key={index}
                    p={2}
                    bg="white"
                    borderRadius="md"
                    boxShadow="sm"
                    borderLeft="3px solid"
                    borderColor={getCategoryColor(log.level)}
                    transition="all 0.2s"
                    _hover={{
                      transform: 'translateX(2px)',
                      boxShadow: 'md'
                    }}
                  >
                    <HStack spacing={1}>
                      <Text
                        fontSize="xs"
                        fontWeight="bold"
                        color={getCategoryColor(log.level)}
                        minW="100px"
                      >
                        [{log.level}]
                      </Text>
                      <Text fontSize="xs" color="gray.700" fontFamily="mono">{log.message}</Text>
                    </HStack>
                  </Box>
                );
              })}
              <div ref={logsEndRef} />
            </VStack>
          )}
        </Box>
      </VStack>
    </Box>
  );
};

export default LogsView; 