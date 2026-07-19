"use client";

import { useEffect, useState } from "react";
import { Globe, BookOpen, Database, RefreshCw, Play, Square, Plus, Trash2, CheckCircle2, AlertCircle, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { apiUrl } from "@/lib/api";

interface Stats {
  conversations?: any;
  rag?: {
    rag_enabled: boolean;
    knowledge_integrator_available: boolean;
    max_knowledge_pieces: number;
    min_relevance_score: number;
    vector_store?: any;
  };
  learning?: {
    total_urls_crawled?: number;
    successful_crawls?: number;
    content_processed?: number;
    knowledge_added?: number;
    duplicates_found?: number;
  };
  learning_active?: boolean;
}

export default function KnowledgeContent() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [urlInput, setUrlInput] = useState("");
  const [urlsToTeach, setUrlsToTeach] = useState<string[]>([]);
  const [teaching, setTeaching] = useState(false);
  const [teachStatus, setTeachStatus] = useState<{ success?: boolean; message?: string } | null>(null);

  const fetchStats = async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(apiUrl("/api/stats"), {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error("Failed to fetch statistics:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const handleAddUrl = () => {
    if (!urlInput.trim()) return;
    try {
      new URL(urlInput);
      if (!urlsToTeach.includes(urlInput.trim())) {
        setUrlsToTeach([...urlsToTeach, urlInput.trim()]);
      }
      setUrlInput("");
    } catch (e) {
      alert("Please enter a valid URL (including http:// or https://)");
    }
  };

  const handleRemoveUrl = (index: number) => {
    setUrlsToTeach(urlsToTeach.filter((_, i) => i !== index));
  };

  const handleTeach = async () => {
    if (urlsToTeach.length === 0) return;
    setTeaching(true);
    setTeachStatus(null);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(apiUrl("/api/learning/learn"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ urls: urlsToTeach }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setTeachStatus({
          success: true,
          message: `Successfully crawled and integrated. Knowledge added: ${data.knowledge_added || 0}, Quality score: ${data.average_quality?.toFixed(2) || "N/A"}`,
        });
        setUrlsToTeach([]);
        fetchStats();
      } else {
        setTeachStatus({
          success: false,
          message: data.error || "Failed to crawl URLs. Please check server logs.",
        });
      }
    } catch (error: any) {
      setTeachStatus({
        success: false,
        message: error.message || "Network error. Failed to connect to server.",
      });
    } finally {
      setTeaching(false);
    }
  };

  const toggleLearningLoop = async (start: boolean) => {
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const endpoint = start ? "/api/learning/start" : "/api/learning/stop";
      const response = await fetch(apiUrl(endpoint), {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
      if (response.ok) {
        setTimeout(fetchStats, 1000);
      }
    } catch (e) {
      console.error(e);
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 space-y-8 p-8 max-w-6xl mx-auto">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b pb-6 border-zinc-800">
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent flex items-center gap-2">
            <Database className="w-8 h-8 text-indigo-400" /> Knowledge Hub
          </h2>
          <p className="text-muted-foreground mt-1">
            Feed URLs into the vector base, configure semantic RAG options, and view ingestion metrics.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant={stats?.learning_active ? "default" : "secondary"} className="text-xs py-1 px-2.5">
            {stats?.learning_active ? "Continuous Loop: Active" : "Continuous Loop: Idle"}
          </Badge>
          <Button variant="outline" size="icon" onClick={fetchStats} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading && "animate-spin"}`} />
          </Button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card className="bg-zinc-900/40 border-zinc-800 backdrop-blur-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-zinc-400">Total Crawled URLs</CardTitle>
            <Globe className="h-5 w-5 text-indigo-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-zinc-100">
              {stats?.learning?.total_urls_crawled ?? 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              URLs fetched from API or RSS sources
            </p>
          </CardContent>
        </Card>

        <Card className="bg-zinc-900/40 border-zinc-800 backdrop-blur-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-zinc-400">Knowledge Chunks</CardTitle>
            <BookOpen className="h-5 w-5 text-purple-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-zinc-100">
              {stats?.learning?.knowledge_added ?? 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Semantic fragments saved to DB
            </p>
          </CardContent>
        </Card>

        <Card className="bg-zinc-900/40 border-zinc-800 backdrop-blur-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-zinc-400">Duplicates Deduplicated</CardTitle>
            <AlertCircle className="h-5 w-5 text-emerald-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-zinc-100">
              {stats?.learning?.duplicates_found ?? 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Filtered semantic overlap items
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="bg-zinc-900/40 border-zinc-800 backdrop-blur-sm flex flex-col justify-between">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-400" /> Teach the Copilot
            </CardTitle>
            <CardDescription>
              Submit custom URLs to instantly crawl, segment, and index. Useful for targeted articles, documents or blogs.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 flex-1">
            <div className="flex gap-2">
              <Input
                placeholder="https://example.com/some-article"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAddUrl()}
                className="border-zinc-800 bg-zinc-950 text-zinc-100 placeholder-zinc-500"
              />
              <Button onClick={handleAddUrl} variant="outline" className="border-zinc-800 hover:bg-zinc-800">
                <Plus className="w-4 h-4 mr-1" /> Add
              </Button>
            </div>

            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3 min-h-[140px] max-h-[220px] overflow-y-auto space-y-2">
              {urlsToTeach.length === 0 ? (
                <div className="text-sm text-zinc-500 italic text-center pt-10">
                  No URLs added. Enter a URL above.
                </div>
              ) : (
                urlsToTeach.map((url, index) => (
                  <div key={index} className="flex items-center justify-between gap-2 p-2 rounded bg-zinc-900 border border-zinc-800 text-xs">
                    <span className="truncate text-zinc-300">{url}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 text-zinc-500 hover:text-red-400 hover:bg-transparent"
                      onClick={() => handleRemoveUrl(index)}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                ))
              )}
            </div>

            {teachStatus && (
              <div className={`p-3 rounded-lg border flex items-start gap-2 text-sm ${
                teachStatus.success
                  ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                  : "bg-red-500/10 border-red-500/20 text-red-400"
              }`}>
                {teachStatus.success ? <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" /> : <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />}
                <span>{teachStatus.message}</span>
              </div>
            )}
          </CardContent>
          <CardFooter className="border-t border-zinc-800 pt-4 flex justify-between items-center">
            <span className="text-xs text-muted-foreground">
              Requires background GPU/CPU nodes configured with PyTorch.
            </span>
            <Button
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold flex items-center gap-2"
              onClick={handleTeach}
              disabled={urlsToTeach.length === 0 || teaching}
            >
              {teaching ? "Ingesting & Deduplicating..." : `Crawl ${urlsToTeach.length} URLs`}
            </Button>
          </CardFooter>
        </Card>

        <div className="space-y-6">
          <Card className="bg-zinc-900/40 border-zinc-800 backdrop-blur-sm">
            <CardHeader>
              <CardTitle>Continuous Ingestion Loop</CardTitle>
              <CardDescription>
                Toggle the background worker loop. When enabled, Celery fetches news, Github events, quote pages, and RSS sources every few minutes.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex justify-between items-center gap-4">
              <div>
                <div className="font-semibold text-sm">Scheduler State</div>
                <div className="text-xs text-muted-foreground mt-0.5">Runs on schedule loops behind Celery</div>
              </div>
              <div className="flex gap-2">
                {stats?.learning_active ? (
                  <Button
                    onClick={() => toggleLearningLoop(false)}
                    variant="destructive"
                    className="gap-2 font-semibold"
                  >
                    <Square className="w-4 h-4" /> Stop Loop
                  </Button>
                ) : (
                  <Button
                    onClick={() => toggleLearningLoop(true)}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white gap-2 font-semibold"
                  >
                    <Play className="w-4 h-4" /> Start Loop
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-zinc-900/40 border-zinc-800 backdrop-blur-sm">
            <CardHeader>
              <CardTitle>Semantic Retrieval Settings</CardTitle>
              <CardDescription>
                Configure vector integration options. Injected context enhances prompts before passing them to the generator.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="flex justify-between border-b border-zinc-800 pb-2">
                <span className="text-zinc-400">RAG Enhancement</span>
                <span className="font-medium text-zinc-200">
                  {stats?.rag?.rag_enabled ? "Enabled" : "Disabled"}
                </span>
              </div>
              <div className="flex justify-between border-b border-zinc-800 pb-2">
                <span className="text-zinc-400">ChromaDB Vector Store</span>
                <span className="font-medium text-zinc-200">
                  {stats?.rag?.knowledge_integrator_available ? "Online" : "Offline"}
                </span>
              </div>
              <div className="flex justify-between border-b border-zinc-800 pb-2">
                <span className="text-zinc-400">Min Relevance Score</span>
                <span className="font-medium text-zinc-200">
                  {stats?.rag?.min_relevance_score ? `${stats.rag.min_relevance_score * 100}%` : "N/A"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">Context Pieces Injected</span>
                <span className="font-medium text-zinc-200">
                  {stats?.rag?.max_knowledge_pieces ?? 0} items
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}