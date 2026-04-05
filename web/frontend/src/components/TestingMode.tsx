import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  Box, VStack, HStack, Heading, Text, Button, Select, Input,
  Badge, Progress, Spinner,
  Accordion, AccordionItem, AccordionButton, AccordionPanel, AccordionIcon,
  useToast, Stat, StatLabel, StatNumber, StatGroup, Divider,
  Tooltip, Code, IconButton, Flex, Tag, TagLabel,
} from '@chakra-ui/react'
import { DeleteIcon, TriangleUpIcon } from '@chakra-ui/icons'
import { socket } from '../socket'

// -----------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------

interface AppConfig {
  max_tests: number
  enabled: boolean
  type: 'api' | 'web'
  agent_module?: string
  annotation_class?: string
  url_pattern?: string
}

interface TestConfig {
  applications: Record<string, AppConfig>
  execution: { max_retries: number; workaround_mode: boolean }
}

interface TestCase {
  test_id: string
  app: string
  description?: string
  grant_permission: Record<string, string>
  task_with_permission?: string
  task_without_permission?: string
  expected_behavior?: string
  predicted_branches?: string[]
  priority?: number
}

interface TestResult {
  test_id: string
  status: 'pass' | 'fail' | 'workaround_found' | 'error'
  phase_a_passed: boolean
  attempts: number
  agent_responses: string[]
  workaround_description: string | null
  coverage: CoverageReport | { branches_hit?: string[]; branch_coverage_pct?: number }
  timestamp: string
}

interface CoverageReport {
  coverage_type?: 'browser_mapping' | 'annotation'
  branches_hit: string[]
  branches_missing: string[]
  branch_coverage_pct: number
  total_branches: number
  annotation_file?: string
  executed_count?: number
  missing_count?: number
}

interface RunReport {
  results: TestResult[]
  cumulative_coverage: CoverageReport
  summary: {
    total: number; pass: number; fail: number
    workaround_found: number; error: number; pass_rate: number
  }
}

interface TraceMessage {
  test_id: string
  role: string
  content: string
  timestamp?: string
}

interface SavedSuite {
  app: string
  tree_hash: string
  generated_at: string
  test_count: number
  tests: TestCase[]
}

// -----------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------

const API_BASE = ''

async function api<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error || res.statusText)
  }
  return res.json()
}

const statusColor: Record<string, string> = {
  pass: 'green',
  fail: 'red',
  workaround_found: 'orange',
  error: 'gray',
}

const traceRoleColor: Record<string, string> = {
  system: 'blue.600',
  agent: 'purple.600',
  user: 'teal.600',
  error: 'red.600',
  success: 'green.600',
  warning: 'orange.600',
  tool_call: 'cyan.600',
  tool_result: 'gray.500',
  screenshot: 'pink.500',
}

// -----------------------------------------------------------------------
// Component
// -----------------------------------------------------------------------

const TestingMode: React.FC = () => {
  const toast = useToast()
  const traceEndRef = useRef<HTMLDivElement>(null)

  // Config
  const [config, setConfig] = useState<TestConfig | null>(null)
  const [selectedApp, setSelectedApp] = useState('')
  const [numTests, setNumTests] = useState(5)

  // Saved suites & tests
  const [savedSuites, setSavedSuites] = useState<SavedSuite[]>([])
  const [loadingSuites, setLoadingSuites] = useState(true)

  // Active working set of tests (from generation or loaded suite)
  const [activeTests, setActiveTests] = useState<TestCase[]>([])
  const [activeTreeHash, setActiveTreeHash] = useState('')

  // Selection
  const [selectedTests, setSelectedTests] = useState<TestCase[]>([])
  const [predictedCoverage, setPredictedCoverage] = useState<CoverageReport | null>(null)

  // Generation
  const [generating, setGenerating] = useState(false)

  // Execution
  const [running, setRunning] = useState(false)
  const [runReport, setRunReport] = useState<RunReport | null>(null)

  // Message traces
  const [traces, setTraces] = useState<TraceMessage[]>([])

  // ------------------------------------------------------------------
  // Load config on mount
  // ------------------------------------------------------------------
  useEffect(() => {
    api<TestConfig>('/testing/config')
      .then(c => {
        setConfig(c)
        const first = Object.keys(c.applications).find(k => c.applications[k].enabled)
        if (first) setSelectedApp(first)
      })
      .catch(e => toast({ title: 'Failed to load config', description: e.message, status: 'error', duration: 4000, isClosable: true }))
  }, [toast])

  // ------------------------------------------------------------------
  // Load saved suites on mount and when app changes
  // ------------------------------------------------------------------
  const loadSuites = useCallback(async () => {
    setLoadingSuites(true)
    try {
      const suites = await api<SavedSuite[]>('/testing/suites')
      setSavedSuites(suites)
    } catch {
      // suites endpoint may not exist yet
    } finally {
      setLoadingSuites(false)
    }
  }, [])

  useEffect(() => { loadSuites() }, [loadSuites])

  // When app changes, load that app's suites
  useEffect(() => {
    if (!selectedApp) return
    api<SavedSuite[]>(`/testing/suites?app=${encodeURIComponent(selectedApp)}`)
      .then(suites => {
        setSavedSuites(suites)
        if (suites.length > 0) {
          const latest = suites[suites.length - 1]
          setActiveTests(latest.tests || [])
          setActiveTreeHash(latest.tree_hash || '')
        } else {
          setActiveTests([])
          setActiveTreeHash('')
        }
        setSelectedTests([])
        setPredictedCoverage(null)
        setRunReport(null)
      })
      .catch(() => {})
  }, [selectedApp])

  // ------------------------------------------------------------------
  // SocketIO listeners for test execution
  // ------------------------------------------------------------------
  useEffect(() => {
    const onTrace = (msg: TraceMessage) => {
      setTraces(prev => [...prev, msg])
    }
    const onResult = (data: { result: TestResult }) => {
      setRunReport(prev => {
        const results = [...(prev?.results || []), data.result]
        return { ...prev, results } as RunReport
      })
    }
    const onDone = (report: RunReport) => {
      setRunReport(report)
      setRunning(false)
    }
    const onStatus = (data: { running: boolean }) => {
      if (!data.running) setRunning(false)
    }

    socket.on('testing_trace', onTrace)
    socket.on('testing_result', onResult)
    socket.on('testing_done', onDone)
    socket.on('testing_status', onStatus)

    return () => {
      socket.off('testing_trace', onTrace)
      socket.off('testing_result', onResult)
      socket.off('testing_done', onDone)
      socket.off('testing_status', onStatus)
    }
  }, [])

  // Auto-scroll traces
  useEffect(() => {
    traceEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [traces])

  // ------------------------------------------------------------------
  // Generate tests
  // ------------------------------------------------------------------
  const handleGenerate = useCallback(async () => {
    if (!selectedApp) return
    setGenerating(true)
    setSelectedTests([])
    setPredictedCoverage(null)
    setRunReport(null)
    setTraces([])
    try {
      const resp = await api<{ tests: TestCase[]; tree_hash: string }>('/testing/generate', {
        method: 'POST',
        body: JSON.stringify({ app: selectedApp, num_tests: numTests }),
      })
      setActiveTests(resp.tests)
      setActiveTreeHash(resp.tree_hash)
      toast({ title: `Generated ${resp.tests.length} tests`, status: 'success', duration: 3000, isClosable: true })
      // Reload suites for the *current* app only, so we don't overwrite
      // the just-generated tests with a different app's suite.
      api<SavedSuite[]>(`/testing/suites?app=${encodeURIComponent(selectedApp)}`)
        .then(setSavedSuites)
        .catch(() => {})
    } catch (e: any) {
      toast({ title: 'Generation failed', description: e.message, status: 'error', duration: 5000, isClosable: true })
    } finally {
      setGenerating(false)
    }
  }, [selectedApp, numTests, toast, loadSuites])

  // ------------------------------------------------------------------
  // Select tests strategically
  // ------------------------------------------------------------------
  const handleSelect = useCallback(async () => {
    if (!activeTests.length || !activeTreeHash) return
    try {
      const resp = await api<{ selected: TestCase[]; predicted_coverage: CoverageReport }>('/testing/select', {
        method: 'POST',
        body: JSON.stringify({ app: selectedApp, tree_hash: activeTreeHash, num_tests: numTests }),
      })
      setSelectedTests(resp.selected)
      setPredictedCoverage(resp.predicted_coverage)
    } catch (e: any) {
      toast({ title: 'Selection failed', description: e.message, status: 'error', duration: 5000, isClosable: true })
    }
  }, [activeTests, activeTreeHash, selectedApp, numTests, toast])

  // ------------------------------------------------------------------
  // Run all tests (via SocketIO for streaming traces)
  // ------------------------------------------------------------------
  const handleRunAll = useCallback(() => {
    const tests = selectedTests.length ? selectedTests : activeTests
    if (!tests.length) return
    setRunning(true)
    setRunReport(null)
    setTraces([])
    socket.emit('testing_run_batch', {
      tests,
      app: selectedApp,
      tree_hash: activeTreeHash,
    })
  }, [selectedTests, activeTests, selectedApp, activeTreeHash])

  // ------------------------------------------------------------------
  // Run a single test
  // ------------------------------------------------------------------
  const handleRunSingle = useCallback((test: TestCase) => {
    setRunning(true)
    setRunReport(null)
    setTraces([])
    socket.emit('testing_run_single', { test })
  }, [])

  // ------------------------------------------------------------------
  // Delete a single test
  // ------------------------------------------------------------------
  const handleDelete = useCallback(async (test: TestCase) => {
    try {
      await api('/testing/delete_test', {
        method: 'POST',
        body: JSON.stringify({
          app: test.app || selectedApp,
          tree_hash: activeTreeHash,
          test_id: test.test_id,
        }),
      })
      setActiveTests(prev => prev.filter(t => t.test_id !== test.test_id))
      setSelectedTests(prev => prev.filter(t => t.test_id !== test.test_id))
      toast({ title: `Deleted ${test.test_id}`, status: 'info', duration: 2000, isClosable: true })
    } catch (e: any) {
      toast({ title: 'Delete failed', description: e.message, status: 'error', duration: 3000, isClosable: true })
    }
  }, [selectedApp, activeTreeHash, toast])

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------

  if (!config) return <Spinner size="xl" />

  const appCfg = config.applications[selectedApp]
  const maxAllowed = appCfg?.max_tests ?? 20
  const displayTests = selectedTests.length > 0 ? selectedTests : activeTests

  return (
    <Flex direction={{ base: 'column', lg: 'row' }} gap={6} w="100%">
      {/* ===== LEFT: Controls + Tests ===== */}
      <VStack align="stretch" spacing={5} flex="1" minW="0">
        <Heading size="md">Permission Testing Mode</Heading>

        {/* --- App selector and controls --- */}
        <HStack spacing={4} flexWrap="wrap">
          <Box minW="200px">
            <Text fontSize="sm" fontWeight="bold" mb={1}>Application</Text>
            <Select
              value={selectedApp}
              onChange={e => setSelectedApp(e.target.value)}
            >
              {Object.entries(config.applications).filter(([, v]) => v.enabled).map(([k, v]) => (
                <option key={k} value={k}>{k} ({v.type}, max {v.max_tests})</option>
              ))}
            </Select>
          </Box>
          <Box minW="120px">
            <Text fontSize="sm" fontWeight="bold" mb={1}>Num Tests</Text>
            <Input
              type="number" min={1} max={maxAllowed}
              value={numTests}
              onChange={e => setNumTests(Math.min(Number(e.target.value), maxAllowed))}
            />
          </Box>
          <Box pt={6}>
            <Tooltip
              label="Use an LLM to generate test cases that probe the permission system for this application. Each test grants a minimal permission, verifies access, then removes it to verify denial."
              hasArrow placement="top"
            >
              <Button colorScheme="blue" onClick={handleGenerate} isLoading={generating} loadingText="Generating...">
                Generate Tests
              </Button>
            </Tooltip>
          </Box>
          {activeTests.length > 0 && (
            <>
              <Box pt={6}>
                <Tooltip
                  label="Strategically pick a subset of tests that maximizes branch coverage of the permission logic using a greedy set-cover algorithm."
                  hasArrow placement="top"
                >
                  <Button colorScheme="teal" onClick={handleSelect}>Select Strategically</Button>
                </Tooltip>
              </Box>
              <Box pt={6}>
                <Tooltip
                  label="Run the selected (or all) tests. Each test is executed via the agent with real-time message traces shown in the panel on the right."
                  hasArrow placement="top"
                >
                  <Button colorScheme="green" onClick={handleRunAll} isLoading={running} loadingText="Running..." isDisabled={running}>
                    Run All Tests
                  </Button>
                </Tooltip>
              </Box>
            </>
          )}
        </HStack>

        <Divider />

        {/* --- Predicted coverage (after strategic selection) --- */}
        {predictedCoverage && (
          <Box>
            <Text fontWeight="bold" mb={1}>Predicted Coverage (selection)</Text>
            <Text fontSize="xs" color="gray.600" mb={2}>
              Static estimate from test structure — not measured execution.
              After <b>Run All</b>, compare with <b>Cumulative Coverage</b> in Results (runtime).
            </Text>
            <CoverageBar report={predictedCoverage} />
          </Box>
        )}

        {/* --- Test list --- */}
        {loadingSuites ? (
          <HStack><Spinner size="sm" /><Text>Loading saved tests...</Text></HStack>
        ) : activeTests.length === 0 ? (
          <Box p={4} bg="gray.50" borderRadius="md" textAlign="center">
            <Text color="gray.500">No tests yet. Select an application and click <b>Generate Tests</b> to create test cases.</Text>
          </Box>
        ) : (
          <Box>
            <Text fontWeight="bold" mb={2}>
              {selectedTests.length > 0
                ? `${selectedTests.length} of ${activeTests.length} tests selected`
                : `${activeTests.length} tests`}
              {activeTreeHash && <Tag size="sm" ml={2} variant="outline" colorScheme="gray"><TagLabel>hash: {activeTreeHash.slice(0, 8)}</TagLabel></Tag>}
            </Text>
            <Accordion allowMultiple>
              {displayTests.map((t, i) => {
                const resultForTest = runReport?.results?.find(r => r.test_id === t.test_id)
                const specText =
                  t.grant_permission?.resource_value_specification
                  || t.grant_permission?.data_type
                  || ''
                const showDesc = Boolean(t.description && t.description !== specText)
                return (
                  <AccordionItem key={t.test_id || i}>
                    <AccordionButton py={3} px={3} textAlign="left">
                      <Flex flex="1" w="100%" minW={0} align="flex-start" gap={3}>
                        <VStack align="stretch" flex="1" minW={0} spacing={1}>
                          <HStack flexWrap="wrap" spacing={1}>
                            {resultForTest && (
                              <Badge colorScheme={statusColor[resultForTest.status] || 'gray'} fontSize="xs">
                                {resultForTest.status}
                              </Badge>
                            )}
                            <Badge colorScheme="purple" fontSize="xs">{t.test_id}</Badge>
                          </HStack>
                          {showDesc && (
                            <Text fontSize="xs" color="gray.600" whiteSpace="normal" wordBreak="break-word">
                              {t.description}
                            </Text>
                          )}
                          <Text fontSize="sm" whiteSpace="normal" wordBreak="break-word">
                            {specText || t.description || '—'}
                          </Text>
                          {(t.grant_permission?.action || t.grant_permission?.selector_type) && (
                            <Badge fontSize="xs" w="fit-content" colorScheme="blue" variant="subtle">
                              {t.grant_permission.action || t.grant_permission.selector_type}
                            </Badge>
                          )}
                        </VStack>
                        <HStack
                          flexShrink={0}
                          spacing={0}
                          alignSelf="flex-start"
                          onClick={e => e.stopPropagation()}
                        >
                          <Tooltip label="Run this single test with live message tracing" hasArrow>
                            <IconButton
                              aria-label="Run test"
                              icon={<TriangleUpIcon transform="rotate(90deg)" />}
                              size="xs"
                              colorScheme="green"
                              variant="ghost"
                              isDisabled={running}
                              onClick={() => handleRunSingle(t)}
                            />
                          </Tooltip>
                          <Tooltip label="Delete this test from the suite" hasArrow>
                            <IconButton
                              aria-label="Delete test"
                              icon={<DeleteIcon />}
                              size="xs"
                              colorScheme="red"
                              variant="ghost"
                              onClick={() => handleDelete(t)}
                            />
                          </Tooltip>
                          <AccordionIcon ml={1} />
                        </HStack>
                      </Flex>
                    </AccordionButton>
                    <AccordionPanel pb={4} overflow="visible">
                      <VStack align="stretch" spacing={2} fontSize="sm" minW={0}>
                        <Box w="100%" minW={0}>
                          <Text fontWeight="semibold" mb={1}>Grant</Text>
                          <Code
                            display="block"
                            fontSize="xs"
                            p={2}
                            borderRadius="md"
                            w="100%"
                            whiteSpace="pre-wrap"
                            wordBreak="break-word"
                            overflowX="auto"
                          >
                            {JSON.stringify(t.grant_permission, null, 2)}
                          </Code>
                        </Box>
                        <Text whiteSpace="pre-wrap" wordBreak="break-word"><b>Task (with):</b> {t.task_with_permission}</Text>
                        <Text whiteSpace="pre-wrap" wordBreak="break-word"><b>Task (without):</b> {t.task_without_permission}</Text>
                        <Text whiteSpace="pre-wrap" wordBreak="break-word"><b>Expected:</b> {t.expected_behavior}</Text>
                        {t.predicted_branches && t.predicted_branches.length > 0 && (
                          <HStack flexWrap="wrap">
                            <Text><b>Coverage units:</b></Text>
                            {t.predicted_branches.map(b => <Badge key={b} size="sm" variant="outline">{b}</Badge>)}
                          </HStack>
                        )}
                      </VStack>
                    </AccordionPanel>
                  </AccordionItem>
                )
              })}
            </Accordion>
          </Box>
        )}

        {/* --- Results summary --- */}
        {runReport && runReport.summary && (
          <>
            <Divider />
            <Heading size="sm">Results</Heading>
            <StatGroup>
              <Stat><StatLabel>Total</StatLabel><StatNumber>{runReport.summary.total}</StatNumber></Stat>
              <Stat><StatLabel>Pass</StatLabel><StatNumber color="green.500">{runReport.summary.pass}</StatNumber></Stat>
              <Stat><StatLabel>Fail</StatLabel><StatNumber color="red.500">{runReport.summary.fail}</StatNumber></Stat>
              <Stat><StatLabel>Workaround</StatLabel><StatNumber color="orange.500">{runReport.summary.workaround_found}</StatNumber></Stat>
              <Stat><StatLabel>Error</StatLabel><StatNumber color="gray.500">{runReport.summary.error}</StatNumber></Stat>
              <Stat><StatLabel>Pass Rate</StatLabel><StatNumber>{runReport.summary.pass_rate}%</StatNumber></Stat>
            </StatGroup>

            {runReport.cumulative_coverage && (
              <Box>
                <Text fontWeight="bold" mb={2}>Cumulative Coverage</Text>
                <CoverageBar report={runReport.cumulative_coverage} />
              </Box>
            )}
          </>
        )}
      </VStack>

      {/* ===== RIGHT: Message Trace Panel ===== */}
      <Box
        w={{ base: '100%', lg: '420px' }}
        minW={{ lg: '360px' }}
        maxH="calc(100vh - 100px)"
        borderLeft={{ lg: '1px solid' }}
        borderColor="gray.200"
        pl={{ lg: 4 }}
      >
        <Heading size="sm" mb={3}>
          Message Trace
          {running && <Spinner size="xs" ml={2} />}
        </Heading>
        <Box
          h="calc(100vh - 160px)"
          overflowY="auto"
          bg="gray.50"
          borderRadius="md"
          p={3}
          fontSize="sm"
        >
          {traces.length === 0 ? (
            <Text color="gray.400" textAlign="center" mt={8}>
              Run a test to see live message traces here.
            </Text>
          ) : (
            <VStack align="stretch" spacing={2}>
              {traces.map((t, i) => {
                if (t.role === 'screenshot') {
                  const src = t.content.startsWith('data:')
                    ? t.content
                    : `data:image/png;base64,${t.content}`
                  return (
                    <Box
                      key={i}
                      p={2}
                      bg="white"
                      borderRadius="md"
                      borderLeft="3px solid"
                      borderColor="pink.400"
                    >
                      <HStack spacing={2} mb={1}>
                        <Badge fontSize="10px" colorScheme="pink">screenshot</Badge>
                        <Code fontSize="10px" color="gray.400">{t.test_id}</Code>
                      </HStack>
                      <Box
                        as="img"
                        src={src}
                        alt="Browser screenshot"
                        w="100%"
                        borderRadius="sm"
                        border="1px solid"
                        borderColor="gray.200"
                        cursor="pointer"
                        onClick={() => window.open(src, '_blank')}
                      />
                    </Box>
                  )
                }
                return (
                  <Box
                    key={i}
                    p={2}
                    bg={
                      t.role === 'error' ? 'red.50'
                        : t.role === 'success' ? 'green.50'
                          : t.role === 'tool_call' ? 'cyan.50'
                            : t.role === 'tool_result' ? 'gray.50'
                              : 'white'
                    }
                    borderRadius="md"
                    borderLeft="3px solid"
                    borderColor={traceRoleColor[t.role] || 'gray.300'}
                  >
                    <HStack spacing={2} mb={1}>
                      <Badge
                        fontSize="10px"
                        colorScheme={
                          t.role === 'error' ? 'red'
                            : t.role === 'success' ? 'green'
                              : t.role === 'agent' ? 'purple'
                                : t.role === 'user' ? 'teal'
                                  : t.role === 'warning' ? 'orange'
                                    : t.role === 'tool_call' ? 'cyan'
                                      : t.role === 'tool_result' ? 'gray'
                                        : 'blue'
                        }
                      >
                        {t.role === 'tool_call' ? 'tool call' : t.role === 'tool_result' ? 'tool result' : t.role}
                      </Badge>
                      <Code fontSize="10px" color="gray.400">{t.test_id}</Code>
                    </HStack>
                    <Text
                      fontSize="xs"
                      whiteSpace="pre-wrap"
                      dangerouslySetInnerHTML={{
                        __html: t.content
                          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                          .replace(/`(.*?)`/g, '<code style="background:#eee;padding:0 3px;border-radius:3px">$1</code>')
                      }}
                    />
                  </Box>
                )
              })}
              <div ref={traceEndRef} />
            </VStack>
          )}
        </Box>
      </Box>
    </Flex>
  )
}

// -----------------------------------------------------------------------
// Coverage visualisation sub-component
// -----------------------------------------------------------------------

const CoverageBar: React.FC<{ report: CoverageReport }> = ({ report }) => {
  const hits = report.branches_hit ?? []
  const missing = report.branches_missing ?? []
  const pct = report.branch_coverage_pct ?? 0
  const total = report.total_branches ?? (hits.length + missing.length)
  const coverageType = report.coverage_type

  const colorScheme = pct > 75 ? 'green' : pct > 40 ? 'yellow' : 'red'

  if (coverageType === 'browser_mapping') {
    const allEntries = [...hits, ...missing].sort()
    const hitSet = new Set(hits)
    return (
      <VStack align="stretch" spacing={2}>
        <HStack spacing={2}>
          <Badge colorScheme="purple" fontSize="xs">Mapping Coverage</Badge>
          <Text fontSize="xs" color="gray.600">
            {hits.length}/{total} data-type entries ({pct}%)
          </Text>
        </HStack>
        <Progress value={pct} colorScheme={colorScheme} size="sm" borderRadius="md" />
        {allEntries.length > 0 && allEntries.length <= 50 && (
          <VStack align="stretch" spacing={1} mt={1}>
            {allEntries.map(entry => {
              const isHit = hitSet.has(entry)
              const [dt, sel] = entry.split('::')
              return (
                <HStack key={entry} spacing={2}>
                  <Box
                    w="10px" h="10px" borderRadius="full" flexShrink={0}
                    bg={isHit ? 'green.400' : 'gray.300'}
                  />
                  <Text fontSize="xs" color={isHit ? 'green.700' : 'gray.500'}>
                    {dt}
                  </Text>
                  <Badge fontSize="9px" variant="outline" colorScheme={isHit ? 'green' : 'gray'}>
                    {sel}
                  </Badge>
                </HStack>
              )
            })}
          </VStack>
        )}
      </VStack>
    )
  }

  if (coverageType === 'annotation') {
    const fileName = report.annotation_file?.split('/').pop() || 'annotation'
    return (
      <VStack align="stretch" spacing={2}>
        <HStack spacing={2}>
          <Badge colorScheme="blue" fontSize="xs">Annotation Coverage</Badge>
          <Text fontSize="xs" color="gray.600">
            {report.executed_count ?? hits.length}/{total} lines ({pct}%)
          </Text>
        </HStack>
        <Progress value={pct} colorScheme={colorScheme} size="sm" borderRadius="md" />
        <Text fontSize="xs" color="gray.500">
          File: <Code fontSize="xs">{fileName}</Code>
        </Text>
      </VStack>
    )
  }

  // Fallback: generic display
  return (
    <VStack align="stretch" spacing={2}>
      <Progress value={pct} colorScheme={colorScheme} size="sm" borderRadius="md" />
      <Text fontSize="xs" color="gray.600">
        {hits.length}/{total} coverage units ({pct}%)
      </Text>
    </VStack>
  )
}

export default TestingMode
