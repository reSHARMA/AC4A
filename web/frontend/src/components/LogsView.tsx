import React, { useState, useEffect } from 'react';
import { Box, VStack, HStack, Text, Select, Input, Button, useToast, InputGroup, InputLeftElement } from '@chakra-ui/react';
import { SearchIcon } from '@chakra-ui/icons';

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

  // Fetch logs from backend
  const fetchLogs = async () => {
    try {
      setIsLoading(true);
      const response = await fetch('/get_logs');
      if (!response.ok) {
        throw new Error('Failed to fetch logs');
      }
      const data = await response.json();
      setLogs(data.logs);
      setFilteredLogs(data.logs);
    } catch (error) {
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

  // Apply filters
  useEffect(() => {
    let filtered = [...logs];

    // Apply level filter
    if (levelFilter !== 'all') {
      filtered = filtered.filter(log => log.level.toLowerCase() === levelFilter.toLowerCase());
    }

    // Apply source filter
    if (sourceFilter !== 'all') {
      filtered = filtered.filter(log => log.source.toLowerCase() === sourceFilter.toLowerCase());
    }

    // Apply search term
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(log => 
        log.message.toLowerCase().includes(term) ||
        log.timestamp.toLowerCase().includes(term)
      );
    }

    setFilteredLogs(filtered);
  }, [logs, levelFilter, sourceFilter, searchTerm]);

  // Fetch logs on component mount
  useEffect(() => {
    fetchLogs();
  }, []);

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
            </VStack>
          )}
        </Box>
      </VStack>
    </Box>
  );
};

export default LogsView; 