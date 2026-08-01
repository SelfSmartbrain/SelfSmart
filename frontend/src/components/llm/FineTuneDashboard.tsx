"use client";

import { useEffect, useRef, useState } from "react";
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  Cpu, 
  HardDrive, 
  Download, 
  Upload,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";

interface FineTuneData {
  epoch: number;
  loss: number;
  learning_rate: number;
  timestamp: string;
}

interface ModelInfo {
  name: string;
  path: string;
  size: string;
  loaded: boolean;
}

interface AdapterInfo {
  name: string;
  path: string;
  epochs: number;
  final_loss: number;
  loaded: boolean;
}

export function FineTuneDashboard({ 
  events, 
  onRefresh 
}: { 
  events: any[]; 
  onRefresh?: () => void; 
}) {
  const [lossHistory, setLossHistory] = useState<number[]>([]);
  const [currentEpoch, setCurrentEpoch] = useState(0);
  const [learningRate, setLearningRate] = useState(0);
  const [isTraining, setIsTraining] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    // Extract loss data from events
    const lossData = events
      .filter(e => e.loss !== undefined || e.payload?.loss !== undefined)
      .map(e => e.loss || e.payload?.loss || e.payload?.final_loss)
      .filter(v => v !== undefined);
    
    setLossHistory(lossData);
    
    const latestEvent = events[events.length - 1];
    if (latestEvent) {
      setCurrentEpoch(latestEvent.epoch || latestEvent.payload?.epoch || 0);
      setLearningRate(latestEvent.learning_rate || latestEvent.payload?.learning_rate || 0);
      setIsTraining(latestEvent.type === "fine_tune_epoch" || latestEvent.type === "fine_tune_loss");
    }
  }, [events]);

  useEffect(() => {
    if (!canvasRef.current) return;
    drawChart();
  }, [lossHistory, canvasRef.current]);

  const drawChart = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
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

    if (lossHistory.length > 1) {
      const minLoss = Math.min(...lossHistory);
      const maxLoss = Math.max(...lossHistory);
      const range = maxLoss - minLoss || 1;

      // Loss line
      ctx.strokeStyle = "#22c55e";
      ctx.lineWidth = 2;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.beginPath();

      lossHistory.forEach((loss, i) => {
        const x = padding + (width - 2 * padding) * i / (lossHistory.length - 1);
        const y = height - padding - (height - 2 * padding) * (loss - minLoss) / range;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();

      // Points
      ctx.fillStyle = "#22c55e";
      lossHistory.forEach((loss, i) => {
        const x = padding + (width - 2 * padding) * i / (lossHistory.length - 1);
        const y = height - padding - (height - 2 * padding) * (loss - minLoss) / range;
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fill();
      });

      // Trend indicator
      if (lossHistory.length >= 2) {
        const trend = lossHistory[lossHistory.length - 1] - lossHistory[lossHistory.length - 2];
        const trendIcon = trend < 0 ? TrendingDown : trend > 0 ? TrendingUp : Minus;
        // Could add trend indicator here
      }
    }

    // Labels
    if (lossHistory.length > 0) {
      const minLoss = Math.min(...lossHistory);
      const maxLoss = Math.max(...lossHistory);
      ctx.fillStyle = "#9ca3af";
      ctx.font = "11px sans-serif";
      ctx.textAlign = "right";
      ctx.fillText(maxLoss.toFixed(4), padding - 5, padding + 12);
      ctx.fillText(minLoss.toFixed(4), padding - 5, height - padding + 4);
      ctx.textAlign = "center";
      ctx.fillText("Epoch", width / 2, height - 5);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header with Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Current Epoch</p>
                <p className="text-2xl font-bold">{currentEpoch}</p>
              </div>
              <Cpu className="w-8 h-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Current Loss</p>
                <p className="text-2xl font-bold text-green-600">
                  {lossHistory[lossHistory.length - 1]?.toFixed(4) || "N/A"}
                </p>
              </div>
              <TrendingDown className="w-8 h-8 text-green-600" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Learning Rate</p>
                <p className="text-2xl font-bold">{learningRate.toExponential(2)}</p>
              </div>
              <HardDrive className="w-8 h-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Status</p>
                <div className="flex items-center gap-2">
                  <Badge variant={isTraining ? "default" : "secondary"}>
                    {isTraining ? "Training" : "Idle"}
                  </Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Loss Chart */}
      <Card className="h-80">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Training Loss</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">{lossHistory.length} data points</Badge>
            <Button variant="ghost" size="icon" onClick={onRefresh} disabled={!onRefresh}>
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="flex-1 p-0">
          <canvas ref={canvasRef} className="w-full h-full" />
        </CardContent>
      </Card>

      {/* Recent Events */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Events</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {events.slice(-10).reverse().map((event, index) => (
              <div key={index} className="flex items-center gap-3 p-2 rounded bg-muted/50 text-sm">
                <div className="w-2 h-2 rounded-full bg-blue-500" />
                <span className="font-mono text-xs text-muted-foreground">
                  {new Date(event.timestamp || Date.now()).toLocaleTimeString()}
                </span>
                <span className="font-medium text-xs">{event.type || "event"}</span>
                {event.loss !== undefined && (
                  <span className="ml-auto font-mono text-green-600">
                    Loss: {event.loss.toFixed(4)}
                  </span>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export function ModelWeightSelector({ 
  models, 
  adapters, 
  currentModel, 
  currentAdapter,
  onModelChange,
  onAdapterChange,
  onLoadAdapter,
  onUnloadAdapter,
}: {
  models: ModelInfo[];
  adapters: AdapterInfo[];
  currentModel: string;
  currentAdapter: string | null;
  onModelChange: (model: string) => void;
  onAdapterChange: (adapter: string | null) => void;
  onLoadAdapter: (path: string) => void;
  onUnloadAdapter: () => void;
}) {
  return (
    <div className="space-y-4">
      {/* Base Model Selector */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="w-5 h-5" />
            Base Model
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
           <Select value={currentModel} onValueChange={(value) => { if (value !== null) onModelChange(value); }}>
            <SelectTrigger>
              <SelectValue placeholder="Select base model" />
            </SelectTrigger>
            <SelectContent>
              {models.map(model => (
                <SelectItem key={model.name} value={model.name} disabled={!model.loaded}>
                  <div className="flex items-center justify-between w-full">
                    <span>{model.name}</span>
                    <span className="text-xs text-muted-foreground">{model.size}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <div className="flex gap-2">
            {models.map(model => (
              <Badge 
                key={model.name} 
                variant={currentModel === model.name ? "default" : "secondary"}
                className={cn("cursor-pointer", currentModel === model.name && "bg-primary")}
              >
                {model.name}
                {model.loaded && <CheckCircle className="w-3 h-3 ml-1" />}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Adapter Selector */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <HardDrive className="w-5 h-5" />
            LoRA Adapters
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Select value={currentAdapter || ""} onValueChange={onAdapterChange}>
            <SelectTrigger>
              <SelectValue placeholder="Select adapter (none for base model)" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">
                <div className="flex items-center justify-between w-full">
                  <span>None (Base Model)</span>
                </div>
              </SelectItem>
              {adapters.map(adapter => (
                <SelectItem key={adapter.name} value={adapter.name} disabled={!adapter.loaded}>
                  <div className="flex flex-col w-full">
                    <div className="flex items-center justify-between">
                      <span>{adapter.name}</span>
                      <span className="text-xs text-muted-foreground">
                        Epochs: {adapter.epochs} • Loss: {adapter.final_loss.toFixed(4)}
                      </span>
                    </div>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="flex flex-wrap gap-2">
            <Badge 
              variant={!currentAdapter ? "default" : "secondary"} 
              className="cursor-pointer"
              onClick={() => onAdapterChange("")}
            >
              None (Base Model)
            </Badge>
            {adapters.map(adapter => (
              <Badge 
                key={adapter.name} 
                variant={currentAdapter === adapter.name ? "default" : "secondary"}
                className="cursor-pointer"
                onClick={() => onAdapterChange(adapter.name)}
              >
                {adapter.name}
                {adapter.loaded && <CheckCircle className="w-3 h-3 ml-1" />}
              </Badge>
            ))}
          </div>

          {currentAdapter && (
            <div className="flex gap-2 pt-2 border-t">
              <Button 
                variant="outline" 
                size="sm" 
                onClick={onUnloadAdapter}
                className="flex-1"
              >
                Unload Adapter
              </Button>
              <Button 
                variant="default" 
                size="sm" 
                onClick={() => onLoadAdapter(adapters.find(a => a.name === currentAdapter)?.path || "")}
                className="flex-1"
              >
                Reload Adapter
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}