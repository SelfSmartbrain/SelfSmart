"use client";

import { useState, useEffect, useRef } from "react";
import { 
  Brain, 
  Search, 
  Code, 
  CheckSquare, 
  Shield, 
  Zap, 
  Pause, 
  Play,
  RotateCcw,
  MessageSquare,
  X,
  Activity,
  Wifi,
  WifiOff,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";

interface AgentNode {
  id: string;
  role: string;
  name: string;
  icon: React.ReactNode;
  color: string;
  status: "idle" | "active" | "completed" | "error";
  progress: number;
  lastThought: string;
  thoughts: string[];
}

interface AgentEvent {
  type: string;
  payload: any;
  timestamp: string;
}

interface WebSocketMessage {
  event_type: string;
  payload: any;
  timestamp: string;
  correlation_id?: string;
}

const AGENT_ROLES: AgentNode[] = [
  {
    id: "planner",
    role: "planner",
    name: "Planner",
    icon: <Brain className="w-5 h-5" />,
    color: "bg-blue-500",
    status: "idle",
    progress: 0,
    lastThought: "",
    thoughts: [],
  },
  {
    id: "researcher",
    role: "researcher",
    name: "Researcher",
    icon: <Search className="w-5 h-5" />,
    color: "bg-green-500",
    status: "idle",
    progress: 0,
    lastThought: "",
    thoughts: [],
  },
  {
    id: "coder",
    role: "coder",
    name: "Coder",
    icon: <Code className="w-5 h-5" />,
    color: "bg-purple-500",
    status: "idle",
    progress: 0,
    lastThought: "",
    thoughts: [],
  },
  {
    id: "evaluator",
    role: "evaluator",
    name: "Evaluator",
    icon: <CheckSquare className="w-5 h-5" />,
    color: "bg-orange-500",
    status: "idle",
    progress: 0,
    lastThought: "",
    thoughts: [],
  },
  {
    id: "safety_gate",
    role: "safety_gate",
    name: "Safety Gate",
    icon: <Shield className="w-5 h-5" />,
    color: "bg-red-500",
    status: "idle",
    progress: 0,
    lastThought: "",
    thoughts: [],
  },
];

const AGENT_CONNECTIONS = [
  { from: "planner", to: "researcher" },
  { from: "researcher", to: "coder" },
  { from: "coder", to: "evaluator" },
  { from: "evaluator", to: "safety_gate" },
];

export default function AgentsPage() {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [connected, setConnected] = useState(false);
  const [agents, setAgents] = useState<AgentNode[]>(AGENT_ROLES);
  const [objective, setObjective] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [fineTuneEvents, setFineTuneEvents] = useState<any[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [showFineTune, setShowFineTune] = useState(false);
  const [modelName, setModelName] = useState<string | null>("Qwen2.5-0.5B");
  const [adapterPath, setAdapterPath] = useState("");
  const [autoFineTune, setAutoFineTune] = useState(true);
  const eventsEndRef = useRef<HTMLDivElement | null>(null);
  const fineTuneEndRef = useRef<HTMLDivElement | null>(null);

  // Draw agent graph on canvas
  useEffect(() => {
    if (canvasRef.current) {
      drawAgentGraph(canvasRef.current, agents);
    }
  }, [agents]);

  useEffect(() => {
    const websocket = new WebSocket("ws://127.0.0.1:8765");
    
    websocket.onopen = () => {
      setConnected(true);
      setWs(websocket); // set the websocket state when the connection opens
      console.log("Connected to agent bridge");
      
      // Subscribe to all event types
      websocket.send(JSON.stringify({
        subscribe: [
          "agent_thought",
          "agent_step",
          "fine_tune_epoch",
          "fine_tune_loss",
          "swarm_status",
          "objective_started",
          "objective_completed",
          "objective_failed",
          "checkpoint_created",
          "consensus_request",
          "consensus_result",
          "error"
        ]
      }));
    };

    websocket.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        handleMessage(message);
      } catch (e) {
        console.error("Failed to parse message:", e);
      }
    };

    websocket.onclose = () => {
      setConnected(false);
      setWs(null); // clear the websocket state when the connection closes
      console.log("Disconnected from agent bridge");
    };

    websocket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    return () => {
      websocket.close();
    };
  }, []); // Empty deps because we only want to run once

  const handleMessage = (message: WebSocketMessage) => {
    const { event_type, payload } = message;
    
    switch (event_type) {
      case "agent_thought":
        updateAgentThought(payload);
        break;
      case "agent_step":
        updateAgentStep(payload);
        break;
      case "fine_tune_epoch":
        addFineTuneEvent(payload);
        break;
      case "fine_tune_loss":
        updateFineTuneLoss(payload);
        break;
      case "swarm_status":
        // Handle swarm status updates
        break;
      case "objective_started":
        setIsRunning(true);
        resetAgents();
        addEvent({ type: "objective_started", payload, timestamp: new Date().toISOString() });
        break;
      case "objective_completed":
        setIsRunning(false);
        addEvent({ type: "objective_completed", payload, timestamp: new Date().toISOString() });
        break;
      case "objective_failed":
        setIsRunning(false);
        addEvent({ type: "objective_failed", payload, timestamp: new Date().toISOString() });
        break;
      case "error":
        addEvent({ type: "error", payload, timestamp: new Date().toISOString() });
        break;
      default:
        // Handle response messages
        if (payload?.response) {
          handleResponse(payload);
        }
    }
  };

  const updateAgentThought = (payload: any) => {
    const { agent, thought, step } = payload;
    setAgents(prev => prev.map(a => {
      if (a.id === agent) {
        const newThoughts = [...a.thoughts, thought];
        return {
          ...a,
          lastThought: thought,
          thoughts: newThoughts.slice(-10), // Keep last 10 thoughts
          status: "active" as const,
          progress: step || a.progress,
        };
      }
      return a;
    }));
    addEvent({ type: "agent_thought", payload, timestamp: new Date().toISOString() });
  };

  const updateAgentStep = (payload: any) => {
    const { agent, status, progress } = payload;
    setAgents(prev => prev.map(a => 
      a.id === agent ? { ...a, status, progress: progress || a.progress } : a
    ));
  };

  const addFineTuneEvent = (payload: any) => {
    setFineTuneEvents(prev => [...prev.slice(-50), { ...payload, timestamp: new Date().toISOString() }]);
  };

  const updateFineTuneLoss = (payload: any) => {
    setFineTuneEvents(prev => prev.map(e => 
      e.epoch === payload.epoch ? { ...e, ...payload } : e
    ));
  };

  const addEvent = (event: AgentEvent) => {
    setEvents(prev => [...prev.slice(-100), event]);
    // Auto-scroll
    setTimeout(() => eventsEndRef.current?.scrollIntoView({ behavior: "smooth" }), 0);
  };

  const handleResponse = (payload: any) => {
    // Handle command responses
    console.log("Response:", payload);
  };

  const resetAgents = () => {
    setAgents(AGENT_ROLES.map(a => ({ ...a, status: "idle" as const, progress: 0, lastThought: "", thoughts: [] })));
    setFineTuneEvents([]);
  };

  const sendCommand = (commandType: string, payload: any) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        command_type: commandType,
        payload,
        request_id: crypto.randomUUID(),
        timestamp: new Date().toISOString(),
      }));
    }
  };

  const handleSubmitObjective = () => {
    if (!objective.trim()) return;
    sendCommand("submit_objective", { objective });
  };

  const handleTriggerFineTune = () => {
    if (!adapterPath.trim()) return;
    sendCommand("trigger_finetune", { adapter_path: adapterPath });
  };

  const handlePauseHarness = () => {
    sendCommand("pause_harness", {});
  };

  const handleResumeHarness = () => {
    sendCommand("resume_harness", {});
  };

  const handleSwitchModel = () => {
    sendCommand("switch_model", { model: modelName });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active": return "bg-green-500 animate-pulse";
      case "completed": return "bg-blue-500";
      case "error": return "bg-red-500";
      default: return "bg-gray-400";
    }
  };

  const getAgentById = (id: string) => agents.find(a => a.id === id);

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar - Agent Graph */}
      <div className="w-80 border-r bg-card flex flex-col">
        <Card className="m-4 h-[120px] flex-1">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center justify-between text-lg">
              <span className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-primary" />
                Agent Swarm
              </span>
              <Badge variant={connected ? "default" : "secondary"} className="text-xs">
                {connected ? <Wifi className="w-3 h-3 mr-1" /> : <WifiOff className="w-3 h-3 mr-1" />}
                {connected ? "Connected" : "Disconnected"}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="relative h-full">
              {/* Agent Graph Canvas */}
              <canvas 
                ref={canvasRef}
                className="w-full h-full"
              />
            </div>
          </CardContent>
          </Card>

          {/* Controls */}
          <Card className="m-4 mb-0 flex-1 min-h-0">
          <Header className="pb-2">
            <CardTitle className="text-lg">Controls</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 space-y-4">
            <div className="space-y-2">
              <Label className="text-xs font-medium">Objective</Label>
              <Textarea
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
                placeholder="Enter objective for the agent swarm..."
                className="min-h-[80px] text-sm"
                disabled={isRunning}
              />
              <Button 
                onClick={handleSubmitObjective}
                disabled={isRunning || !objective.trim() || !connected}
                className="w-full"
                size="lg"
              >
                {isRunning ? <Pause className="w-4 h-4 mr-2" /> : <Play className="w-4 h-4 mr-2" />}
                {isRunning ? "Running..." : "Submit Objective"}
              </Button>
            </div>

            <Separator />

            <div className="space-y-2">
              <Label className="text-xs font-medium">Model</Label>
              <Select 
                value={modelName} 
                onValueChange={(value) => {
                  if (value !== null) setModelName(value);
                }}
              >
                <SelectTrigger className="text-sm">
                  <SelectValue placeholder="Select model" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Qwen2.5-0.5B">Qwen2.5-0.5B</SelectItem>
                  <SelectItem value="Llama-3.2-1B">Llama-3.2-1B</SelectItem>
                  <SelectItem value="Phi-3.5-mini">Phi-3.5-mini</SelectItem>
                </SelectContent>
              </Select>
              <Button 
                onClick={handleSwitchModel}
                disabled={isRunning || !connected}
                variant="outline"
                className="w-full"
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Switch Model
              </Button>
            </div>

            <Separator />

            <div className="space-y-2">
              <Label className="text-xs font-medium">Auto Fine-Tune</Label>
              <div className="flex items-center justify-between">
                <span className="text-sm">Enabled</span>
                <input
                  type="checkbox"
                  checked={autoFineTune}
                  onChange={(e) => setAutoFineTune(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
                />
              </div>
              <Input
                placeholder="Adapter path (e.g., data/adapters/requirement_adapter)"
                value={adapterPath}
                onChange={(e) => setAdapterPath(e.target.value)}
                className="text-sm"
              />
              <Button 
                onClick={handleTriggerFineTune}
                disabled={isRunning || !adapterPath.trim() || !connected}
                variant="outline"
                className="w-full"
              >
                Trigger Fine-Tune
              </Button>
            </div>

            <Separator />

            <div className="flex gap-2">
              <Button 
                onClick={handlePauseHarness}
                disabled={!isRunning || !connected}
                variant="outline"
                className="flex-1"
              >
                <Pause className="w-4 h-4 mr-1" />
                Pause
              </Button>
              <Button 
                onClick={handleResumeHarness}
                disabled={!isRunning || !connected}
                variant="outline"
                className="flex-1"
              >
                <Play className="w-4 h-4 mr-1" />
                Resume
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Tabs */}
        <Tabs defaultValue="stream" className="flex-1 flex flex-col">
          <TabsList className="border-b p-2">
            <TabsTrigger value="stream">Agent Stream</TabsTrigger>
            <TabsTrigger value="fintune">Fine-Tune Monitor</TabsTrigger>
            <TabsTrigger value="details">Agent Details</TabsTrigger>
          </TabsList>

          <TabsContent value="stream" className="flex-1 flex flex-col overflow-hidden">
            <div className="flex-1 overflow-hidden">
              <ScrollArea className="h-full p-4 space-y-2">
                {events.map((event, index) => (
                  <EventCard key={index} event={event} />
                ))}
                <div ref={eventsEndRef} />
              </ScrollArea>
            </div>
          </TabsContent>

          <TabsContent value="fintune" className="flex-1 flex flex-col overflow-hidden">
            <FineTuneMonitor 
              events={fineTuneEvents} 
              ref={fineTuneEndRef}
            />
          </TabsContent>

          <TabsContent value="details" className="flex-1 flex flex-col overflow-hidden">
            <AgentDetailsPanel agents={agents} selectedAgent={selectedAgent} onSelectAgent={setSelectedAgent} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

// Agent Graph Canvas Drawing
function drawAgentGraph(canvas: HTMLCanvasElement, agents: AgentNode[]) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  const width = rect.width;
  const height = rect.height;
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) * 0.35;

  // Clear
  ctx.clearRect(0, 0, width, height);

  // Agent positions (circular layout)
  const positions: Record<string, { x: number; y: number }> = {};
  agents.forEach((agent, i) => {
    const angle = (i / agents.length) * Math.PI * 2 - Math.PI / 2;
    positions[agent.id] = {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    };
  });

  // Draw connections
  ctx.strokeStyle = "rgba(100, 100, 100, 0.3)";
  ctx.lineWidth = 2;
  AGENT_CONNECTIONS.forEach(conn => {
    const from = positions[conn.from];
    const to = positions[conn.to];
    if (from && to) {
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();
    }
  });

  // Draw agents
  agents.forEach(agent => {
    const pos = positions[agent.id];
    
    // Get status color inline
    const statusColor = 
      agent.status === "active" ? "#22c55e" :
      agent.status === "completed" ? "#3b82f6" :
      agent.status === "error" ? "#ef4444" : "#9ca3af";
    
    // Outer glow for active
    if (agent.status === "active") {
      const gradient = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, 40);
      gradient.addColorStop(0, agent.color.replace("bg-", "").replace("-500", "") + "40");
      gradient.addColorStop(1, "transparent");
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 40, 0, Math.PI * 2);
      ctx.fill();
    }

    // Agent circle
    const statusColorValue = statusColor;
    ctx.fillStyle = statusColorValue;
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, 28, 0, Math.PI * 2);
    ctx.fill();

    // Inner circle for progress
    if (agent.progress > 0) {
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 3;
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 24, -Math.PI / 2, -Math.PI / 2 + (agent.progress / 100) * Math.PI * 2);
      ctx.stroke();
    }

    // Icon would be drawn here - simplified with text
    ctx.fillStyle = "#fff";
    ctx.font = "bold 14px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(agent.name.charAt(0), pos.x, pos.y);

    // Label
    ctx.fillStyle = "#fff";
    ctx.font = "11px sans-serif";
    ctx.fillText(agent.name, pos.x, pos.y + 42);
  });
}

// Event Card Component
interface EventCardProps {
  event: AgentEvent;
}

function EventCard({ event }: EventCardProps) {
  const icons: Record<string, React.ReactNode> = {
    agent_thought: <MessageSquare className="w-4 h-4 text-blue-500" />,
    agent_step: <Zap className="w-4 h-4 text-purple-500" />,
    objective_started: <Play className="w-4 h-4 text-green-500" />,
    objective_completed: <CheckSquare className="w-4 h-4 text-blue-500" />,
    objective_failed: <X className="w-4 h-4 text-red-500" />,
    error: <Shield className="w-4 h-4 text-red-500" />,
  };

  const Icon = icons[event.type] || <Activity className="w-4 h-4" />;

  return (
    <div className="flex gap-2 text-sm p-2 rounded-lg bg-muted/50 border">
      <div className="flex-shrink-0 text-muted-foreground">
        {Icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-xs capitalize">{event.type.replace("_", " ")}</span>
          <span className="text-xs text-muted-foreground">
            {new Date(event.timestamp).toLocaleTimeString()}
          </span>
        </div>
        <pre className="text-xs text-muted-foreground mt-1 overflow-x-auto whitespace-pre-wrap">
          {JSON.stringify(event.payload, null, 2)}
        </pre>
      </div>
    </div>
  );
}

// Fine-Tune Monitor Component
interface FineTuneMonitorProps {
  events: any[];
  ref?: React.RefObject<HTMLDivElement | null>;
}

function FineTuneMonitor({ events, ref }: FineTuneMonitorProps) {
  if (events.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <div className="text-center">
          <Activity className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>No fine-tune events yet</p>
          <p className="text-sm">Fine-tune events will appear here when triggered</p>
        </div>
      </div>
    );
  }

  const latestEvent = events[events.length - 1];
  const epochs = events.filter(e => e.type === "fine_tune_epoch" || e.undefined !== undefined);

  return (
    <div className="flex-1 flex flex-col overflow-hidden p-4 space-y-4">
      {/* Loss Chart */}
      <Card className="flex-1">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              Training Loss
              <Badge variant="secondary">{epochs.length} epochs</Badge>
            </CardTitle>
          </CardHeader>
        <CardContent className="flex-1">
          <LossChart epochs={epochs} ref={ref} />
        </CardContent>
      </Card>

      {/* Event Log */}
      <Card className="h-64">
        <CardHeader>
          <CardTitle>Event Log</CardTitle>
        </Header>
        <CardContent>
          <ScrollArea className="h-full">
            <div className="space-y-1">
              {events.slice(-20).reverse().map((event, index) => (
                <div key={index} className="text-xs p-2 rounded bg-muted/50 font-mono">
                  <span className="text-muted-foreground">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </span>
                  <span className="ml-2 font-medium">{event.type || "event"}</span>
                  <pre className="mt-1 text-[10px] text-muted-foreground">
                    {JSON.stringify(event.payload || event, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}

// Loss Chart Component
interface LossChartProps {
  epochs: any[];
  ref?: React.RefObject<HTMLDivElement | null>;
}

function LossChart({ epochs, ref }: LossChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || epochs.length === 0) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;
    const padding = 40;

    // Clear
    ctx.clearRect(0, 0, width, height);

    // Grid
    ctx.strokeStyle = "rgba(100, 100, 100, 0.1)";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 10; i++) {
      const y = padding + (height - 2 * padding) * i / 10;
      ctx.beginPath();
      ctx.moveTo(padding, y);
      ctx.lineTo(width - padding, y);
      ctx.stroke();
    }
    for (let i = 0; i <= 10; i++) {
      const x = padding + (width - 2 * padding) * i / 10;
      ctx.beginPath();
      ctx.moveTo(x, padding);
      ctx.lineTo(x, height - padding);
      ctx.stroke();
    }

    // Data
    const lossData = epochs
      .map(e => e.loss || e.payload?.loss || e.payload?.final_loss)
      .filter(v => v !== undefined);
    
    let minLoss = 0;
    let maxLoss = 0;
    if (lossData.length > 0) {
      minLoss = Math.min(...lossData);
      maxLoss = Math.max(...lossData);
    }

    // Draw line and points only if we have at least two points
    if (lossData.length > 1) {
      const range = maxLoss - minLoss || 1;

      ctx.strokeStyle = "#22c55e";
      ctx.lineWidth = 2;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.beginPath();

      lossData.forEach((loss, i) => {
        const x = padding + (width - 2 * padding) * i / (lossData.length - 1);
        const y = height - padding - (height - 2 * padding) * (loss - minLoss) / range;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();

      // Points
      ctx.fillStyle = "#22c55e";
      lossData.forEach((loss, i) => {
        const x = padding + (width - 2 * padding) * i / (lossData.length - 1);
        const y = height - padding - (height - 2 * padding) * (loss - minLoss) / range;
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fill();
      });
    }

    // Draw labels if we have data
    if (lossData.length > 0) {
      ctx.fillStyle = "#9ca3af";
      ctx.font = "11px sans-serif";
      ctx.textAlign = "right";
      ctx.fillText(maxLoss.toFixed(3), padding - 5, padding + 12);
      ctx.fillText(minLoss.toFixed(3), padding - 5, height - padding + 4);
      ctx.textAlign = "center";
      ctx.fillText("Epoch", width / 2, height - 5);
    }
  }, [epochs]);

  return (
    <div className="h-full w-full" ref={ref}>
      <canvas ref={canvasRef} className="h-full w-full" />
    </div>
  );
}

// Agent Details Panel
interface AgentDetailsPanelProps {
  agents: AgentNode[];
  selectedAgent: string | null;
  onSelectAgent: (id: string | null) => void;
}

function AgentDetailsPanel({ agents, selectedAgent, onSelectAgent }: AgentDetailsPanelProps) {
  const agent = selectedAgent ? agents.find(a => a.id === selectedAgent) : null;

  if (!agent) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <p>Click an agent in the graph to view details</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden p-4 space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${agent.color}`}>
              {agent.icon}
            </div>
            <div>
              <h3 className="text-xl font-bold">{agent.name}</h3>
              <Badge variant={agent.status === "active" ? "default" : agent.status === "error" ? "destructive" : "secondary"}>
                {agent.status}
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label className="text-xs font-medium">Progress</Label>
            <div className="w-full bg-secondary rounded-full h-2 mt-1">
              <div 
                className={`h-2 rounded-full transition-all duration-300 ${agent.color.replace("bg-", "bg-")}`}
                style={{ width: `${agent.progress}%` }}
              />
            </div>
            <div className="text-sm text-muted-foreground mt-1">{agent.progress}% complete</div>
          </div>

          <div>
            <Label className="text-xs font-medium">Latest Thought</Label>
            <p className="text-sm mt-1 whitespace-pre-wrap">{agent.lastThought || "No thoughts yet"}</p>
          </div>

          <div>
            <Label className="text-xs font-medium">Thought History</Label>
            <ScrollArea className="h-64 mt-1">
              <div className="space-y-2">
                {agent.thoughts.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No thoughts recorded</p>
                ) : (
                  agent.thoughts.map((thought, index) => (
                    <div key={index} className="text-xs p-2 rounded bg-muted/50 border-l-2 border-primary">
                      <span className="text-muted-foreground">#{agent.thoughts.length - index}</span>
                      <p className="mt-1">{thought}</p>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}