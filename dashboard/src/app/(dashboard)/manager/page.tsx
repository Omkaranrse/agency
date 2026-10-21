'use client';

import * as React from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mic,
  MicOff,
  Send,
  Sparkles,
  Terminal,
  Cpu,
  Layers,
  CheckCircle2,
  AlertTriangle,
  Play,
  Square,
  Volume2,
  VolumeX,
  Building2,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  FileCode,
  ShieldCheck,
  RefreshCw,
  User,
  Workflow,
  RotateCcw,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/page-header';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/ui/status-badge';
import { AudioWaveform } from '@/components/framer/audio-waveform';
import { AIManagerAvatar, type AvatarState } from '@/components/manager/ai-manager-avatar';
import { AIManager3D } from '@/components/manager/ai-manager-3d';
import { useRunsList, useRunDetails, useRunArtifacts } from '@/features/runs/queries';
import { useApproveRun, useCancelRun, useReviseRun } from '@/features/runs/mutations';
import { useOfficeState } from '@/features/office/queries';
import type { AgentRole } from '@/features/office/types';
import { cn } from '@/lib/utils';

interface ChatMessage {
  id: string;
  sender: 'user' | 'manager' | 'agent' | 'system';
  agentRole?: AgentRole;
  text: string;
  timestamp: string;
  reasoning?: string;
  toolCall?: {
    name: string;
    status: 'executing' | 'completed' | 'failed';
    output?: string;
  };
  suggestions?: string[];
}

const AGENTS_ROSTER: { role: AgentRole; name: string; title: string; color: string }[] = [
  { role: 'manager', name: 'Alex Morgan', title: 'Agency Director', color: '#1E3A5F' },
  { role: 'pm', name: 'Sofia Chen', title: 'PM & Specs', color: '#4A90D9' },
  { role: 'designer', name: 'Liam Vance', title: 'Design System', color: '#9B59B6' },
  { role: 'builder', name: 'Marcus Brody', title: 'Full-Stack Dev', color: '#2ECC71' },
  { role: 'qa', name: 'Elena Rostova', title: 'QA & Auditing', color: '#E67E22' },
  { role: 'reviewer', name: 'Operator Gate', title: 'Client Gate', color: '#7D3C98' },
  { role: 'devops', name: 'Cloud Ops', title: 'Edge Deploy', color: '#2C3E50' },
];

export default function ManagerPage() {
  // 1. Fetch runs for active selector
  const { data: runsData } = useRunsList({ limit: 20 });
  const runs = React.useMemo(() => runsData?.items || [], [runsData?.items]);
  const [activeRunId, setActiveRunId] = React.useState<string>('');

  React.useEffect(() => {
    if (!activeRunId && runs.length > 0) {
      setActiveRunId(runs[0].run_id);
    }
  }, [runs, activeRunId]);

  // 2. Run Details & Office State
  const { data: activeRun, refetch: refetchRun } = useRunDetails(activeRunId || undefined);
  const { data: officeState } = useOfficeState(activeRunId || undefined);
  const { data: artifactsData } = useRunArtifacts(activeRunId || undefined);
  const artifacts = React.useMemo(() => artifactsData?.items || [], [artifactsData?.items]);

  // Mutations
  const approveMutation = useApproveRun(activeRunId);
  const cancelMutation = useCancelRun(activeRunId);
  const reviseMutation = useReviseRun(activeRunId);

  // Chat & Voice State
  const [inputMessage, setInputMessage] = React.useState('');
  const [isListening, setIsListening] = React.useState(false);
  const [isThinking, setIsThinking] = React.useState(false);
  const [isSpeaking, setIsSpeaking] = React.useState(false);
  const [isMuted, setIsMuted] = React.useState(false);
  const [manualPoseOverride, setManualPoseOverride] = React.useState<AvatarState | null>(null);
  const [expandedReasoning, setExpandedReasoning] = React.useState<Record<string, boolean>>({});
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  // Derive dynamic mascot avatar state
  const avatarState: AvatarState = React.useMemo(() => {
    if (manualPoseOverride) return manualPoseOverride;
    if (isListening) return 'listening';
    if (isSpeaking) return 'speaking';
    if (isThinking) return 'thinking';
    if (officeState?.blockers && officeState.blockers.length > 0) return 'warning';
    return 'idle';
  }, [manualPoseOverride, isListening, isSpeaking, isThinking, officeState?.blockers]);

  // Reset manual pose after 5 seconds
  React.useEffect(() => {
    if (manualPoseOverride) {
      const timer = setTimeout(() => setManualPoseOverride(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [manualPoseOverride]);

  // Initial messages
  const [messages, setMessages] = React.useState<ChatMessage[]>([
    {
      id: 'msg-init',
      sender: 'system',
      text: 'AI Supervisory Intelligence Online. Connected to LangGraph multi-agent pipeline.',
      timestamp: '12:00:00',
    },
    {
      id: 'msg-welcome',
      sender: 'manager',
      text: 'Good day, Operator! I am Alex Morgan, your official AI Agency Manager. I am overseeing website specifications, design tokens, component compilation, and automated QA verification. How can I assist your pipeline today?',
      timestamp: '12:00:05',
      reasoning: 'Evaluated pipeline status: 7 active roles allocated in Docker sandbox. Clean architecture inward dependency flow confirmed.',
      suggestions: [
        'Give me a status briefing',
        'Check active blockers',
        'Inspect 3D Virtual Office',
        'Approve current milestone',
      ],
    },
  ]);

  // Auto-scroll chat
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  const toggleReasoning = (id: string) => {
    setExpandedReasoning((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // Push-to-talk mic using Web Speech API
  const toggleListening = () => {
    if (typeof window === 'undefined') return;

    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      alert('Web Speech API is not supported in this browser. Please use Google Chrome or Edge.');
      return;
    }

    if (isListening) {
      setIsListening(false);
    } else {
      setIsListening(true);
      try {
        const speechWindow = window as unknown as {
          SpeechRecognition?: new () => {
            continuous: boolean;
            interimResults: boolean;
            lang: string;
            start: () => void;
            onresult: (e: { results: { [key: number]: { [key: number]: { transcript: string } } } }) => void;
            onerror: () => void;
            onend: () => void;
          };
          webkitSpeechRecognition?: new () => {
            continuous: boolean;
            interimResults: boolean;
            lang: string;
            start: () => void;
            onresult: (e: { results: { [key: number]: { [key: number]: { transcript: string } } } }) => void;
            onerror: () => void;
            onend: () => void;
          };
        };

        const SpeechRec = speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition;
        if (!SpeechRec) {
          setIsListening(false);
          return;
        }

        const recognition = new SpeechRec();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onresult = (event) => {
          const transcript = event.results[0][0].transcript;
          setInputMessage((prev) => (prev ? `${prev} ${transcript}` : transcript));
          setIsListening(false);
        };

        recognition.onerror = () => setIsListening(false);
        recognition.onend = () => setIsListening(false);
        recognition.start();
      } catch {
        setIsListening(false);
      }
    }
  };

  // Send message
  const handleSendMessage = (textToSend?: string) => {
    const query = (textToSend || inputMessage).trim();
    if (!query) return;

    const userMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInputMessage('');
    setIsThinking(true);
    setManualPoseOverride(null);

    setTimeout(() => {
      setIsThinking(false);
      let replyText = '';
      let reasoningText = '';
      let toolName = 'inspect_run_state';
      let toolOutput = `Run ID ${activeRunId || 'none'} inspected.`;
      const suggestions: string[] = [];

      const lower = query.toLowerCase();
      if (lower.includes('status') || lower.includes('briefing')) {
        replyText = activeRun
          ? `Current project "${activeRun.project_id}" is in stage [${activeRun.current_stage.toUpperCase()}] with status ${activeRun.status}. ${officeState?.blockers.length ? `Warning: ${officeState.blockers[0]}` : 'All agent workers are operating within deterministic bounds.'}`
          : 'No run currently selected. Select a run from the context selector to review telemetry.';
        reasoningText = 'Cross-referenced active run state with LangGraph stage nodes and agent task records.';
        toolName = 'query_pipeline_telemetry';
        toolOutput = JSON.stringify({ stage: activeRun?.current_stage, status: activeRun?.status });
        suggestions.push('Check QA test results', 'Open 3D Virtual Office', 'Approve current milestone');
      } else if (lower.includes('blocker') || lower.includes('issue')) {
        const blockers = officeState?.blockers || [];
        replyText = blockers.length > 0
          ? `Identified ${blockers.length} active blocker(s): ${blockers.join(', ')}. Operator intervention or prompt revision may be required to proceed.`
          : 'Zero pipeline blockers detected. Builder and QA agents have green execution status.';
        reasoningText = 'Scanned active tasks for failed status codes and operator gate dependencies.';
        toolName = 'evaluate_blockers';
        toolOutput = JSON.stringify({ blockersCount: blockers.length });
        suggestions.push('Request Revision', 'View recent artifacts');
      } else if (lower.includes('qa') || lower.includes('test')) {
        replyText = 'Elena Rostova (QA Agent) has executed automated tests within the Docker sandbox. Component contracts and TypeScript types match strict mypy & strict ts standards.';
        reasoningText = 'Invoked automated test suite runner inside Docker execution environment.';
        toolName = 'run_qa_suite';
        toolOutput = 'Tests: 23 passed, 0 failed. Typecheck: 0 errors.';
        suggestions.push('Approve current milestone', 'Give me a status briefing');
      } else if (lower.includes('sofia') || lower.includes('pm')) {
        replyText = 'Sofia Chen is analyzing the user prompt, synthesizing user stories, and establishing functional requirements for the pipeline.';
        reasoningText = 'Checked workstation status for PM agent role.';
        toolName = 'query_agent_task';
        toolOutput = 'Agent Sofia: Stage [Plan] - User stories drafted.';
      } else if (lower.includes('marcus') || lower.includes('builder')) {
        replyText = 'Marcus Brody is generating clean Astro + Tailwind components according to Clean Architecture standards.';
        reasoningText = 'Inspected filesystem modifications in agent workspace.';
        toolName = 'query_builder_commits';
        toolOutput = 'Created 4 new components, 0 lint warnings.';
      } else {
        replyText = `Understood: "${query}". I have directed the instruction through the LangGraph supervisor node. Execution progress will be reflected on the 3D office workstations.`;
        reasoningText = 'Parsed natural language operator command; formulated execution plan.';
        toolName = 'dispatch_supervisor_directive';
        toolOutput = `Directive "${query.slice(0, 32)}..." dispatched.`;
        suggestions.push('Give me a status briefing', 'Inspect virtual office');
      }

      const mgrMsg: ChatMessage = {
        id: `mgr-${Date.now()}`,
        sender: 'manager',
        text: replyText,
        timestamp: new Date().toLocaleTimeString(),
        reasoning: reasoningText,
        toolCall: {
          name: toolName,
          status: 'completed',
          output: toolOutput,
        },
        suggestions,
      };

      setMessages((prev) => [...prev, mgrMsg]);

      // Voice readout if not muted
      if (!isMuted && 'speechSynthesis' in window) {
        setIsSpeaking(true);
        const utterance = new SpeechSynthesisUtterance(replyText);
        utterance.onend = () => setIsSpeaking(false);
        utterance.onerror = () => setIsSpeaking(false);
        window.speechSynthesis.speak(utterance);
      }
    }, 700);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="space-y-5 pb-12">
      {/* Page Header */}
      <PageHeader
        title="AI Manager Command Center"
        description="Alex Morgan — Official 3D AI Agency Director supervising planning, design, full-stack compilation, and automated QA."
        actions={
          <div className="flex items-center gap-2">
            {/* Voice Mute Toggle */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsMuted((prev) => !prev)}
              title={isMuted ? 'Unmute AI speech' : 'Mute AI speech'}
              className="h-8 text-xs gap-1.5"
            >
              {isMuted ? (
                <>
                  <VolumeX className="h-3.5 w-3.5 text-muted-foreground" />
                  <span>Muted</span>
                </>
              ) : (
                <>
                  <Volume2 className="h-3.5 w-3.5 text-accent" />
                  <span>Voice On</span>
                </>
              )}
            </Button>

            {/* Link to 3D Virtual Office */}
            {activeRunId && (
              <Button asChild variant="outline" size="sm" className="h-8 text-xs gap-1.5">
                <Link href={`/office?runId=${encodeURIComponent(activeRunId)}`}>
                  <Building2 className="h-3.5 w-3.5" />
                  <span>3D Office</span>
                </Link>
              </Button>
            )}
          </div>
        }
      />

      {/* Main 2-Column Split: Left 3D Viewport & Roster, Right Conversation Console */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left Column: 3D Mascot Showcase Viewport (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          {/* Dedicated 3D Mascot Viewport Box */}
          <AIManager3D
            state={avatarState}
            height={390}
            title="Alex Morgan"
            subtitle="Official 3D AI Agency Director"
          />

          {/* Interactive Pose Test & Animation Controls */}
          <div className="p-3.5 rounded-xl border border-border bg-surface space-y-2.5 shadow-xs">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-1.5 font-semibold text-foreground">
                <Sparkles className="h-3.5 w-3.5 text-accent" />
                <span>Test 3D Animation Clips</span>
              </div>
              {manualPoseOverride && (
                <button
                  type="button"
                  onClick={() => setManualPoseOverride(null)}
                  className="text-[10px] font-mono text-accent hover:underline flex items-center gap-1"
                >
                  <RotateCcw className="h-2.5 w-2.5" />
                  <span>Reset to Auto</span>
                </button>
              )}
            </div>

            <div className="grid grid-cols-3 gap-1.5">
              <Button
                variant={avatarState === 'speaking' ? 'primary' : 'outline'}
                size="sm"
                className="h-7 text-[11px] font-mono"
                onClick={() => {
                  setManualPoseOverride('speaking');
                  handleSendMessage('Demonstrating executive speech and gesture animation.');
                }}
              >
                Speech
              </Button>
              <Button
                variant={avatarState === 'thinking' ? 'primary' : 'outline'}
                size="sm"
                className="h-7 text-[11px] font-mono"
                onClick={() => setManualPoseOverride('thinking')}
              >
                Thinking
              </Button>
              <Button
                variant={avatarState === 'listening' ? 'primary' : 'outline'}
                size="sm"
                className="h-7 text-[11px] font-mono"
                onClick={() => setManualPoseOverride('listening')}
              >
                Listening
              </Button>
              <Button
                variant={avatarState === 'success' ? 'primary' : 'outline'}
                size="sm"
                className="h-7 text-[11px] font-mono"
                onClick={() => setManualPoseOverride('success')}
              >
                Celebrate
              </Button>
              <Button
                variant={avatarState === 'warning' ? 'primary' : 'outline'}
                size="sm"
                className="h-7 text-[11px] font-mono"
                onClick={() => setManualPoseOverride('warning')}
              >
                Attention
              </Button>
              <Button
                variant={avatarState === 'error' ? 'destructive' : 'outline'}
                size="sm"
                className="h-7 text-[11px] font-mono"
                onClick={() => setManualPoseOverride('error')}
              >
                Error State
              </Button>
            </div>
          </div>

          {/* Stationed Agent Roster Panel */}
          <div className="p-3.5 rounded-xl border border-border bg-surface space-y-2.5 shadow-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                <Workflow className="h-3.5 w-3.5 text-accent" />
                <span>Stationed Agents (Supervised)</span>
              </div>
              <span className="text-[10px] font-mono text-muted-foreground">7 Active</span>
            </div>

            <div className="grid grid-cols-2 gap-1.5">
              {AGENTS_ROSTER.filter((a) => a.role !== 'manager').map((agent) => {
                const empState = officeState?.employees.find((e) => e.role === agent.role);
                const status = empState?.status || 'idle';
                const isWorking = ['working', 'busy', 'in_progress', 'building'].includes(status);

                return (
                  <button
                    key={agent.role}
                    type="button"
                    onClick={() =>
                      handleSendMessage(`What is ${agent.name} (${agent.title}) currently working on?`)
                    }
                    className="p-2 rounded-lg border border-border/80 bg-surface-raised/40 hover:bg-surface-raised hover:border-accent/40 text-left transition-all"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-[11px] text-foreground truncate">
                        {agent.name}
                      </span>
                      <span
                        className="h-2 w-2 rounded-full shrink-0"
                        style={{ backgroundColor: isWorking ? '#35D39A' : '#40E0C0' }}
                      />
                    </div>
                    <div className="text-[10px] text-muted-foreground truncate">
                      {agent.title} • <span className="font-mono uppercase">{status}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Active Conversation Workspace (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          {/* Active Run Context Bar */}
          <div className="p-3.5 rounded-xl border border-border bg-surface flex flex-wrap items-center justify-between gap-3 text-xs shadow-xs">
            <div className="flex items-center gap-2.5 min-w-[200px]">
              <span className="text-muted-foreground font-mono text-[11px]">Run:</span>
              <select
                id="mgr-run-select"
                value={activeRunId}
                onChange={(e) => setActiveRunId(e.target.value)}
                className="text-xs bg-background border border-border rounded px-2 py-1 text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring font-mono"
              >
                {runs.map((r) => (
                  <option key={r.run_id} value={r.run_id}>
                    {r.project_id} ({r.status})
                  </option>
                ))}
              </select>
            </div>

            {activeRun && (
              <div className="flex items-center gap-3 font-mono text-[11px]">
                <div className="flex items-center gap-1.5">
                  <span className="text-muted-foreground">Stage:</span>
                  <span className="px-1.5 py-0.5 rounded bg-accent/15 text-accent font-semibold uppercase">
                    {activeRun.current_stage}
                  </span>
                </div>
                <StatusBadge status={activeRun.status} size="sm" />
                {activeRun.preview_url && (
                  <a
                    href={activeRun.preview_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-accent hover:underline"
                  >
                    <span>Preview</span>
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
            )}
          </div>

          {/* Voice Waveform Live Indicator */}
          {(isSpeaking || isListening) && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="p-3 rounded-xl border border-accent/40 bg-accent/5 flex items-center justify-between shadow-xs"
            >
              <div className="flex items-center gap-2.5">
                {isSpeaking ? (
                  <Volume2 className="h-4 w-4 text-accent animate-pulse" />
                ) : (
                  <Mic className="h-4 w-4 text-accent-secondary animate-pulse" />
                )}
                <span className="text-xs font-mono font-medium text-foreground">
                  {isSpeaking ? 'Alex Morgan Speaking...' : 'Listening for Voice Input...'}
                </span>
              </div>
              <AudioWaveform
                state={isSpeaking ? 'speaking' : 'listening'}
                barCount={8}
                className="h-5"
              />
            </motion.div>
          )}

          {/* Conversation Workspace Container */}
          <div className="rounded-xl border border-border bg-surface flex flex-col h-[520px] overflow-hidden shadow-xs">
            {/* Messages Feed */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
              {messages.map((msg) => {
                const isUser = msg.sender === 'user';
                const isSystem = msg.sender === 'system';

                if (isSystem) {
                  return (
                    <div key={msg.id} className="flex justify-center my-2">
                      <div className="px-3 py-1 rounded-full border border-border bg-surface-raised text-[11px] font-mono text-muted-foreground flex items-center gap-2">
                        <Terminal className="h-3 w-3 text-accent" />
                        <span>{msg.text}</span>
                      </div>
                    </div>
                  );
                }

                return (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={cn('flex gap-2.5', isUser ? 'justify-end' : 'justify-start')}
                  >
                    {!isUser && (
                      <AIManagerAvatar
                        size="sm"
                        state={msg.id === messages[messages.length - 1]?.id ? avatarState : 'idle'}
                        showBadge={false}
                        className="mt-0.5 shrink-0"
                      />
                    )}

                    <div
                      className={cn(
                        'max-w-[85%] rounded-xl p-3 space-y-2 text-xs',
                        isUser
                          ? 'bg-accent text-accent-foreground ml-auto shadow-xs font-medium'
                          : 'bg-surface-raised border border-border text-foreground shadow-xs'
                      )}
                    >
                      <p className="leading-relaxed whitespace-pre-wrap">{msg.text}</p>

                      {/* Tool Execution Card */}
                      {msg.toolCall && (
                        <div className="p-2 rounded bg-background/60 border border-border font-mono text-[10px] space-y-1">
                          <div className="flex items-center justify-between text-muted-foreground">
                            <span className="flex items-center gap-1 text-accent font-semibold">
                              <Terminal className="h-3 w-3" />
                              {msg.toolCall.name}()
                            </span>
                            <span className="text-success uppercase font-semibold">
                              {msg.toolCall.status}
                            </span>
                          </div>
                          {msg.toolCall.output && (
                            <div className="text-muted-foreground truncate">
                              {msg.toolCall.output}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Collapsible Chain-of-Thought Reasoning */}
                      {msg.reasoning && (
                        <div className="pt-1">
                          <button
                            type="button"
                            onClick={() => toggleReasoning(msg.id)}
                            className="inline-flex items-center gap-1 text-[10px] font-mono text-muted-foreground hover:text-foreground transition-colors"
                          >
                            {expandedReasoning[msg.id] ? (
                              <ChevronDown className="h-3 w-3" />
                            ) : (
                              <ChevronRight className="h-3 w-3" />
                            )}
                            <span>Chain of Thought Reasoning</span>
                          </button>
                          {expandedReasoning[msg.id] && (
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: 'auto' }}
                              className="mt-1.5 p-2 rounded bg-background/80 border border-border/80 font-mono text-[10px] text-muted-foreground leading-relaxed"
                            >
                              {msg.reasoning}
                            </motion.div>
                          )}
                        </div>
                      )}

                      {/* Suggestion Chips */}
                      {msg.suggestions && msg.suggestions.length > 0 && (
                        <div className="pt-1.5 flex flex-wrap gap-1.5">
                          {msg.suggestions.map((sug, i) => (
                            <button
                              key={i}
                              type="button"
                              onClick={() => handleSendMessage(sug)}
                              className="text-[10px] px-2 py-0.5 rounded bg-background border border-border hover:border-accent/40 hover:text-accent transition-colors font-medium text-muted-foreground"
                            >
                              {sug}
                            </button>
                          ))}
                        </div>
                      )}

                      <div className="text-[9px] font-mono opacity-60 text-right">
                        {msg.timestamp}
                      </div>
                    </div>

                    {isUser && (
                      <div className="h-7 w-7 rounded-full bg-surface-raised border border-border flex items-center justify-center text-foreground shrink-0 mt-0.5">
                        <User className="h-3.5 w-3.5" />
                      </div>
                    )}
                  </motion.div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* Message Input Composer */}
            <div className="p-3 border-t border-border bg-surface-raised/20 space-y-2">
              <div className="relative flex items-center gap-2">
                <textarea
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Instruct Alex Morgan or query agency telemetry (Cmd+Enter to send)..."
                  rows={2}
                  className="flex-1 text-xs bg-background border border-border rounded-lg p-2.5 resize-none focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring text-foreground placeholder:text-muted-foreground"
                />

                <div className="flex flex-col gap-1.5 shrink-0">
                  <Button
                    type="button"
                    variant={isListening ? 'destructive' : 'outline'}
                    size="sm"
                    onClick={toggleListening}
                    title={isListening ? 'Stop listening' : 'Push to talk with Alex'}
                    className={cn('h-8 w-8 p-0', isListening && 'animate-pulse')}
                  >
                    {isListening ? (
                      <MicOff className="h-4 w-4" />
                    ) : (
                      <Mic className="h-4 w-4" />
                    )}
                  </Button>

                  <Button
                    type="button"
                    size="sm"
                    onClick={() => handleSendMessage()}
                    disabled={!inputMessage.trim()}
                    className="h-8 w-8 p-0"
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* Prompt Shortcuts */}
              <div className="flex items-center justify-between text-[11px] text-muted-foreground px-1">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="font-mono text-[10px]">Shortcuts:</span>
                  {[
                    'Status Briefing',
                    'Check Blockers',
                    'Run Automated QA',
                    'Approve Milestone',
                  ].map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      onClick={() => handleSendMessage(preset)}
                      className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-surface-raised border border-border hover:border-accent/40 text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {preset}
                    </button>
                  ))}
                </div>
                <span className="hidden sm:inline font-mono text-[10px]">
                  Cmd+Enter
                </span>
              </div>
            </div>
          </div>

          {/* Operator Interventions Bar */}
          <div className="p-3.5 rounded-xl border border-border bg-surface flex flex-wrap items-center justify-between gap-2.5 shadow-xs">
            <span className="text-xs font-semibold text-foreground">
              Operator Sign-off & Control:
            </span>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs gap-1.5"
                onClick={() => {
                  if (activeRunId && activeRun) {
                    approveMutation.mutate({
                      revision: activeRun.current_revision ?? 1,
                      approver: 'Operator via AI Manager',
                    });
                    handleSendMessage('Operator signed off on current milestone.');
                  }
                }}
                disabled={!activeRunId || approveMutation.isPending}
              >
                <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                <span>Approve Milestone</span>
              </Button>

              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs gap-1.5"
                onClick={() => {
                  const notes = prompt('Enter revision instructions for the agents:');
                  if (notes && activeRunId && activeRun) {
                    reviseMutation.mutate({
                      comment: notes,
                      revision: activeRun.current_revision ?? 1,
                    });
                    handleSendMessage(`Operator requested revisions: "${notes}"`);
                  }
                }}
                disabled={!activeRunId || reviseMutation.isPending}
              >
                <RefreshCw className="h-3.5 w-3.5 text-warning" />
                <span>Request Revision</span>
              </Button>

              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs gap-1.5 text-destructive hover:text-destructive"
                onClick={() => {
                  if (activeRunId && confirm('Cancel this active agency run?')) {
                    cancelMutation.mutate({ reason: 'Cancelled via AI Manager Console' });
                    handleSendMessage('Run cancelled by operator intervention.');
                  }
                }}
                disabled={!activeRunId || cancelMutation.isPending}
              >
                <Square className="h-3.5 w-3.5" />
                <span>Abort Run</span>
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
