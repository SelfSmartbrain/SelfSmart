"use client";

import { useEffect, useState } from "react";
import { Settings, Cpu, HardDrive, Shield, CheckCircle, AlertTriangle, Loader2, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { apiUrl } from "@/lib/api";

interface SystemStatus {
  status: string;
  app_name: string;
  version: string;
  debug: boolean;
  llm_provider: string;
  llm_api_key_configured: boolean;
  embeddings: string;
  features: string[];
}

interface TrainingStatus {
  task_id: string;
  status: string;
  result: { error?: string } | null;
}

export default function SettingsContent() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const setTrainingTaskId = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("training_task_id");
    }
    return null;
  })[1];
  const [trainingStatus, setTrainingStatus] = useState<TrainingStatus | null>(null);
  const [trainingLoading, setTrainingLoading] = useState(false);

  useEffect(() => {
    let mounted = true;

    const fetchData = async () => {
      if (!mounted) return;
      try {
        const response = await fetch(apiUrl("/status"));
        if (response.ok) {
          const data = await response.json();
          if (mounted) {
            setStatus(data);
          }
        }
      } catch {
        console.error("Failed to fetch system status:");
      }
    };

    fetchData();

    return () => {
      mounted = false;
    };
  }, []);

  const handleStartTraining = async () => {
    setTrainingLoading(true);
    setTrainingStatus(null);
    try {
      const response = await fetch(apiUrl("/api/training/start"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        }
      });
      const data = await response.json();
      if (response.ok && data.success && data.task_id) {
        setTrainingTaskId(data.task_id);
        if (typeof window !== "undefined") {
          localStorage.setItem("training_task_id", data.task_id);
        }
        setTrainingStatus({
          task_id: data.task_id,
          status: "PENDING",
          result: null
        });
      } else {
        alert(data.message || "Failed to trigger training");
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      alert("Error triggering training: " + message);
    } finally {
      setTrainingLoading(false);
    }
  };

  return (
    <div className="flex-1 space-y-8 p-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="border-b pb-6 border-zinc-800">
        <h2 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-400 to-emerald-400 bg-clip-text text-transparent flex items-center gap-2">
          <Settings className="w-8 h-8 text-indigo-400" /> System Settings
        </h2>
        <p className="text-muted-foreground mt-1">
          Monitor LLM integrations, embeddings configurations, and fine-tune your local model.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Connection status */}
        <Card className="bg-zinc-900/40 border-zinc-800 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-zinc-100">
              <Shield className="w-5 h-5 text-indigo-400" /> Model Configuration
            </CardTitle>
            <CardDescription>
              Details about the currently connected active text generation models and APIs.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
              <span className="text-zinc-400">System Name</span>
              <span className="font-semibold text-zinc-200">{status?.app_name || "SelfSmart AI"}</span>
            </div>
            <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
              <span className="text-zinc-400">LLM Provider</span>
              <Badge variant="outline" className="border-zinc-700 text-zinc-200 capitalize">
                {status?.llm_provider || "N/A"}
              </Badge>
            </div>
            <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
              <span className="text-zinc-400">API Key Configured</span>
              <span className="font-medium text-zinc-200 flex items-center gap-1">
                {status?.llm_api_key_configured ? (
                  <>
                    <CheckCircle className="w-4 h-4 text-emerald-500" /> Yes
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-4 h-4 text-amber-500" /> No API Key
                  </>
                )}
              </span>
            </div>
            <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
              <span className="text-zinc-400">Embeddings</span>
              <span className="font-semibold text-zinc-300 text-xs bg-zinc-950 px-2.5 py-1 rounded-md border border-zinc-800">
                {status?.embeddings || "N/A"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-zinc-400">App Version</span>
              <span className="font-mono text-zinc-300">{status?.version || "1.0.0"}</span>
            </div>
          </CardContent>
        </Card>

        {/* Features card */}
        <Card className="bg-zinc-900/40 border-zinc-800 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-zinc-100">
              <Cpu className="w-5 h-5 text-indigo-400" /> System Features
            </CardTitle>
            <CardDescription>
              Status of feature integrations active within the server.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {status?.features.map((feature, i) => (
                <Badge key={i} className="bg-zinc-950 border border-zinc-800 text-zinc-300 text-xs py-1 px-2.5 capitalize hover:bg-zinc-950">
                  {feature.replace(/_/g, " ")}
                </Badge>
              )) || (
                <div className="text-sm text-zinc-500 italic">No features discovered</div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Fine tuning card */}
      <Card className="bg-zinc-900/40 border-zinc-800 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-zinc-100">
            <HardDrive className="w-5 h-5 text-indigo-400" /> Model Fine-Tuning (LoRA)
          </CardTitle>
          <CardDescription>
            Trigger an offline LoRA self-training script using Celery. This aligns the LLM directly with new knowledge gathered by the crawler and conversation history logs.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-4 text-sm text-zinc-300 space-y-2">
            <h4 className="font-semibold text-zinc-200">How training works:</h4>
            <ul className="list-disc pl-5 space-y-1 text-xs text-zinc-400">
              <li>Ingested texts are formatted into QA pairs using LLM instructions.</li>
              <li>A LoRA layer is compiled and trained using PyTorch on user-provided data.</li>
              <li>The trained checkpoint is loaded into memory to assist local LLM streams.</li>
            </ul>
          </div>

          {trainingStatus && (
            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-zinc-400">Training Task ID:</span>
                <span className="font-mono text-zinc-300 text-xs">{trainingStatus.task_id}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-zinc-400">Status:</span>
                <Badge variant={
                  trainingStatus.status === "SUCCESS" ? "default" :
                  trainingStatus.status === "FAILURE" ? "destructive" : "secondary"
                }>
                  {trainingStatus.status}
                </Badge>
              </div>
              {trainingStatus.status === "PENDING" && (
                <div className="flex items-center gap-2 text-xs text-indigo-400 mt-2">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Task is queued. Training will take a few minutes...</span>
                </div>
              )}
            </div>
          )}

          {trainingStatus && trainingStatus.status === "SUCCESS" && (
            <div className="rounded-lg border border-zinc-800 bg-emerald-500/10 p-4 space-y-2">
              <div className="flex items-center gap-2 text-xs text-emerald-400">
                <CheckCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>Training completed successfully! Check the task result for details.</span>
              </div>
            </div>
          )}

          {trainingStatus && trainingStatus.status === "FAILURE" && (
            <div className="rounded-lg border border-zinc-800 bg-red-500/10 p-4 space-y-2">
              <div className="flex items-center gap-2 text-xs text-red-400">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>Training failed: {trainingStatus.result?.error || "Unknown error"}</span>
              </div>
            </div>
          )}
        </CardContent>
        <CardFooter className="border-t border-zinc-800 pt-4 flex justify-between items-center">
          <span className="text-xs text-muted-foreground">
            Requires background GPU/CPU nodes configured with PyTorch.
          </span>
          <Button
            onClick={handleStartTraining}
            disabled={trainingLoading || (trainingStatus?.status === "PENDING")}
            className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold flex items-center gap-2"
          >
            {trainingLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            Trigger Model Fine-Tuning
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}