import React, { useEffect, useState } from "react";
import { HStack, Select, Text, Box } from '@chakra-ui/react';

const MODES = [
  { value: "ask", label: "Ask" },
  { value: "skip", label: "Skip" },
  { value: "infer", label: "Infer" },
  { value: "yolo", label: "YOLO" },
];

const MODE_KEY = "permission_management_mode";

interface PermissionModeSelectorProps {
  compact?: boolean;
  label?: string;
  onModeChange?: (mode: string) => void;
}

export default function PermissionModeSelector({ compact = false, label = "Permission Management Mode:", onModeChange }: PermissionModeSelectorProps) {
  const [mode, setMode] = useState<string>(() => {
    // Load from localStorage or default to "ask"
    console.log("Loading mode from localStorage:", localStorage.getItem(MODE_KEY));
    return localStorage.getItem(MODE_KEY) || "ask";
  });

  useEffect(() => {
    localStorage.setItem(MODE_KEY, mode);
    if (onModeChange) onModeChange(mode);
  }, [mode, onModeChange]);

  if (compact) {
    return (
      <HStack spacing={2}>
        <Text fontSize="md" color="gray.600" fontWeight="medium">{label}</Text>
        <Select
          size="sm"
          width="90px"
          value={mode}
          onChange={e => setMode(e.target.value)}
          bg="gray.50"
          borderColor="gray.300"
          borderRadius="md"
          fontWeight="medium"
        >
          {MODES.map(m => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </Select>
      </HStack>
    );
  }

  return (
    <Box my={3}>
      <Text mb={1} fontWeight="medium">{label}</Text>
      <Select
        value={mode}
        onChange={e => setMode(e.target.value)}
        width="200px"
        bg="gray.50"
        borderColor="gray.300"
        borderRadius="md"
        fontWeight="medium"
      >
        {MODES.map(m => (
          <option key={m.value} value={m.value}>
            {m.label}
          </option>
        ))}
      </Select>
    </Box>
  );
} 