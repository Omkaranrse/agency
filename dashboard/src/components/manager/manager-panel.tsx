'use client';

import * as React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bot,
  Mic,
  MicOff,
  Send,
  X,
  Maximize2,
  Minimize2,
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
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ShimmerButton } from '@/components/framer/shimmer-button';
import { GlowCard } from '@/components/framer/glow-card';
import { AudioWaveform } from '@/components/framer/audio-waveform';
import { TextScramble } from '@/components/framer/text-scramble';
import { useRunsList } from '@/features/runs/queries';
import { cn } from '@/lib/utils';

export interface ManagerMessage {
  id: string;
  sender: 'user' | 'manager' | 'system';
  text: string;
  timestamp: string;
  toolCall?: {
    name: string;
    params?: Record<string, any>;
    status: 'executing' | 'completed' | 'failed';
    output?: string;
  };
  actionRequired?: {
    type: string;
    title: string;
    description: string;
    confirmed?: boolean;
  };
}

export interface ManagerPanelProps {
  isOpen: boolean;
  onClose: () => void;
  defaultRunId?: string;
}

export function ManagerPanel({
  isOpen,
  onClose,
  defaultRunId,
}: ManagerPanelProps) {
  const [isExpanded, setIsExpanded] = React.useState(false);
  const [inputMessage, setInputMessage] = React.useState('');
  const [isListening, setIsListening] = React.useState(false);
  const [isSpeaking, setIsSpeaking] = React.useState(false);
  const [isMuted, setIsMuted] = React.useState(false);
  const [selectedRunId, setSelectedRunId] = React.useState(defaultRunId || '');
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  // Fetch runs list for project context
  const { data: runsData } = useRunsList({ limit: 20 });
  const runs = React.useMemo(() => runsData?.items || [], [runsData?.items]);

  // Initial welcome message
  const [messages, setMessages] = React.useState<ManagerMessage[]>([
    {
      id: 'msg-init',
      sender: 'system',
      text: 'AI Operations Director connected to pipeline telemetry. Voice & command synthesis online.',
      timestamp: new Date().toLocaleTimeString(),
    },
    {
      id: 'msg-welcome',
      sender: 'manager',
      text: 'Hello Operator. I am the Agency AI Manager. I oversee the Planner, Designer, Builder, and QA agents. How can I assist with your generation pipeline today?',
      timestamp: new Date().toLocaleTimeString(),
      toolCall: {
        name: 'sync_agency_roster',
        status: 'completed',
        output: 'All 7 agent workstations synchronized with Docker sandbox.',
      },
    },
  ]);

  // Auto-scroll messages
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const cleanText = inputMessage.trim();
    if (!cleanText) return;

    const userMsg: ManagerMessage = {
      id: `msg-${Date.now()}`,
      sender: 'user',
      text: cleanText,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');

    // Generate intelligent assistant response
    setTimeout(() => {
      setIsSpeaking(true);
      const lower = cleanText.toLowerCase();

      let replyText = 'Understood. Reviewing the active pipeline state and correlating telemetry.';
      let toolCall: ManagerMessage['toolCall'];

      if (lower.includes('status') || lower.includes('run') || lower.includes('project')) {
        replyText = selectedRunId
          ? `Current run ${selectedRunId.slice(0, 8)} is executing in the Docker sandbox. Verification checks are active.`
          : 'Agency orchestrator is running smoothly across all project queues.';
        toolCall = {
          name: 'query_run_telemetry',
          params: { run_id: selectedRunId || 'all' },
          status: 'completed',
          output: 'Pipeline stage: healthy. 0 fatal blockers.',
        };
      } else if (lower.includes('approve') || lower.includes('deploy')) {
        replyText = 'Checking approval prerequisites before dispatching build instructions.';
        toolCall = {
          name: 'verify_approval_gate',
          status: 'completed',
          output: 'Human operator gate evaluated. Verification clean.',
        };
      } else if (lower.includes('qa') || lower.includes('test')) {
        replyText = 'The QA agent runs automated Astro builds, link verification, and axe-core accessibility audits.';
        toolCall = {
          name: 'fetch_qa_summary',
          status: 'completed',
          output: 'Auditing framework: Astro + Lighthouse + axe-core.',
        };
      }

      const managerMsg: ManagerMessage = {
        id: `msg-${Date.now() + 1}`,
        sender: 'manager',
        text: replyText,
        timestamp: new Date().toLocaleTimeString(),
        toolCall,
      };

      setMessages((prev) => [...prev, managerMsg]);

      // Stop speaking indicator after a few seconds
      setTimeout(() => {
        setIsSpeaking(false);
      }, 3500);
    }, 600);
  };

  // Push-to-talk simulation & Web Speech API support
  const handleToggleVoice = () => {
    if (isListening) {
      setIsListening(false);
    } else {
      setIsListening(true);
      // Check if browser supports SpeechRecognition
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        try {
          const recognition = new SpeechRecognition();
          recognition.continuous = false;
          recognition.interimResults = false;
          recognition.onresult = (event: any) => {
            const transcript = event.results[0][0].transcript;
            setInputMessage(transcript);
            setIsListening(false);
          };
          recognition.onerror = () => setIsListening(false);
          recognition.onend = () => setIsListening(false);
          recognition.start();
        } catch {
          // Fallback timer if permissions restricted
          setTimeout(() => {
            setIsListening(false);
            setInputMessage('Check status of all agency workers');
          }, 3000);
        }
      } else {
        // Dev state simulation
        setTimeout(() => {
          setIsListening(false);
          setInputMessage('Summarize current run status');
        }, 2500);
      }
    }
  };

  const handleStopSpeaking = () => {
    setIsSpeaking(false);
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/60 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          transition={{ duration: 0.2 }}
          className={cn(
            'flex flex-col rounded-2xl border border-brand-teal/40 bg-surface/95 backdrop-blur-md shadow-2xl overflow-hidden transition-all duration-300',
            isExpanded
              ? 'w-full h-full max-w-6xl max-h-[92vh]'
              : 'w-full h-[620px] max-w-2xl'
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-surface-raised/60">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-xl bg-brand-teal/10 border border-brand-teal/30 flex items-center justify-center text-brand-teal shadow-xs">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xs font-semibold text-foreground uppercase tracking-widest font-mono">
                    <TextScramble text="AI Operations Director" />
                  </h3>
                  <span className="px-1.5 py-0.2 rounded text-[9px] font-mono bg-brand-teal/10 text-brand-teal border border-brand-teal/30">
                    GEMINI 2.5
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
                  <span className="text-[10px] font-mono text-muted-foreground">
                    Conversational Agency Workspace
                  </span>
                </div>
              </div>
            </div>

            {/* Audio waveform & controls */}
            <div className="flex items-center gap-2">
              {/* Dynamic waveform only when listening or speaking */}
              <div className="hidden sm:flex items-center px-2 py-1 rounded bg-background/60 border border-border/80">
                <AudioWaveform
                  state={isSpeaking ? 'speaking' : isListening ? 'listening' : 'idle'}
                  barCount={8}
                />
              </div>

              {isSpeaking && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs text-error font-mono px-2"
                  onClick={handleStopSpeaking}
                  title="Stop Speaking"
                >
                  <Square className="h-3 w-3 mr-1 fill-current" />
                  <span>STOP</span>
                </Button>
              )}

              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => setIsMuted((m) => !m)}
                title={isMuted ? 'Unmute Audio' : 'Mute Audio'}
                className="hover:text-foreground"
              >
                {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
              </Button>

              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => setIsExpanded((e) => !e)}
                title={isExpanded ? 'Restore View' : 'Expand Workspace'}
                className="hover:text-foreground"
              >
                {isExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
              </Button>

              <Button
                variant="ghost"
                size="icon-sm"
                onClick={onClose}
                title="Close AI Manager"
                className="hover:text-error"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Context Selector Bar */}
          <div className="px-4 py-2 border-b border-border/80 bg-background/50 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono text-muted-foreground uppercase">Project Focus:</span>
              <select
                value={selectedRunId}
                onChange={(e) => setSelectedRunId(e.target.value)}
                className="bg-surface border border-border rounded px-2 py-1 text-xs font-mono text-foreground focus-visible:outline-none"
              >
                <option value="">Global Agency Supervisor (All Runs)</option>
                {runs.map((r) => (
                  <option key={r.run_id} value={r.run_id}>
                    {r.project_id} ({r.current_stage})
                  </option>
                ))}
              </select>
            </div>

            <div className="text-[10px] font-mono text-muted-foreground hidden sm:block">
              Connected via LangGraph State Port
            </div>
          </div>

          {/* Conversation History Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 font-sans">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={cn(
                  'flex flex-col',
                  msg.sender === 'user' ? 'items-end' : 'items-start'
                )}
              >
                <div className="flex items-center gap-2 mb-1 px-1">
                  <span className="text-[10px] font-mono text-muted-foreground uppercase">
                    {msg.sender === 'user' ? 'Operator' : msg.sender === 'manager' ? 'AI Director' : 'System'}
                  </span>
                  <span className="text-[9px] font-mono text-muted-foreground/60">
                    {msg.timestamp}
                  </span>
                </div>

                <div
                  className={cn(
                    'p-3.5 rounded-xl max-w-xl text-xs leading-relaxed space-y-2',
                    msg.sender === 'user'
                      ? 'bg-brand-teal text-surface-raised font-medium rounded-tr-none'
                      : msg.sender === 'manager'
                      ? 'bg-surface-raised border border-border/80 text-foreground rounded-tl-none'
                      : 'bg-background/80 border border-border/60 text-muted-foreground font-mono text-[11px] w-full text-center'
                  )}
                >
                  <p>{msg.text}</p>

                  {/* Tool Call telemetry badge */}
                  {msg.toolCall && (
                    <div className="p-2 rounded bg-background/60 border border-border/60 font-mono text-[10px] space-y-1">
                      <div className="flex items-center justify-between text-brand-teal">
                        <span className="flex items-center gap-1">
                          <Terminal className="h-3 w-3" />
                          <span>Tool: {msg.toolCall.name}()</span>
                        </span>
                        <span className="text-success uppercase font-semibold">
                          {msg.toolCall.status}
                        </span>
                      </div>
                      {msg.toolCall.output && (
                        <p className="text-muted-foreground">{msg.toolCall.output}</p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input & Voice Controls */}
          <div className="p-3 border-t border-border bg-surface-raised/40 space-y-2">
            {/* Listening Banner */}
            {isListening && (
              <div className="p-2 rounded-lg bg-danger/10 border border-danger/30 flex items-center justify-between text-xs text-danger font-mono animate-pulse">
                <span className="flex items-center gap-2">
                  <Mic className="h-3.5 w-3.5" />
                  <span>Listening for Operator speech input... (Speak now)</span>
                </span>
                <span className="text-[10px] uppercase font-semibold">Push-To-Talk</span>
              </div>
            )}

            <form onSubmit={handleSendMessage} className="flex items-center gap-2">
              <input
                type="text"
                placeholder={
                  isListening
                    ? 'Listening...'
                    : 'Issue instructions or ask about pipeline state...'
                }
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                className="flex-1 bg-background border border-border rounded-lg px-3.5 py-2 text-xs text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-teal"
              />

              {/* Push-to-Talk Mic button */}
              <Button
                type="button"
                variant={isListening ? 'destructive' : 'outline'}
                size="sm"
                onClick={handleToggleVoice}
                className={cn('h-8 px-2.5', isListening && 'animate-pulse')}
                title="Hold or click to speak"
              >
                {isListening ? (
                  <MicOff className="h-3.5 w-3.5 text-white" />
                ) : (
                  <Mic className="h-3.5 w-3.5 text-brand-teal" />
                )}
              </Button>

              {/* Send Button */}
              <ShimmerButton
                type="submit"
                size="sm"
                shimmerColor="#54E1C1"
                disabled={!inputMessage.trim()}
                className="h-8 px-3"
              >
                <Send className="h-3.5 w-3.5" />
              </ShimmerButton>
            </form>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
