"use client";

import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Brain,
  Database,
  MessageSquare,
  ThumbsUp,
  Loader2,
  Wifi,
  WifiOff,
} from "lucide-react";
import { apiUrl } from "@/lib/api";

interface DashboardData {
  knowledge_base: { chunk_count: number; rag_enabled: boolean };
  feedback: { total: number; positive: number; satisfaction_rate: number };
  conversations: { total: number };
  system: {
    llm_provider: string;
    uptime_seconds: number;
    version: string;
    learning_active: boolean;
  };
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  loading,
  accent,
}: {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ElementType;
  loading: boolean;
  accent?: string;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        {loading ? (
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        ) : (
          <>
            <div className="text-2xl font-bold">{value}</div>
            <p className={`text-xs ${accent ?? "text-muted-foreground"}`}>
              {subtitle}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchDashboard = async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      setError("Not authenticated — please log in.");
      setLoading(false);
      return;
    }
    try {
      const res = await fetch(apiUrl("/api/dashboard"), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Backend returned HTTP ${res.status}`);
      const json: DashboardData = await res.json();
      setData(json);
      setError(null);
      setLastUpdated(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
    const interval = setInterval(fetchDashboard, 30_000);
    return () => clearInterval(interval);
  }, []);

  const satisfactionPct = data
    ? Math.round(data.feedback.satisfaction_rate * 100)
    : 0;

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">System Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Live metrics for SelfSmart AI
            {data && (
              <span className="ml-2 text-xs font-mono">
                v{data.system.version} · {data.system.llm_provider} ·
                uptime {formatUptime(data.system.uptime_seconds)}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          {error ? (
            <>
              <WifiOff className="h-4 w-4 text-destructive" />
              <span className="text-destructive">Disconnected</span>
            </>
          ) : (
            <>
              <Wifi className="h-4 w-4 text-green-500" />
              <span className="text-muted-foreground">
                {lastUpdated
                  ? `Updated ${lastUpdated.toLocaleTimeString()}`
                  : "Connecting..."}
              </span>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3">
          <p className="text-sm text-destructive">⚠ {error}</p>
        </div>
      )}

      {/* Stat Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Knowledge Chunks"
          value={data ? data.knowledge_base.chunk_count.toLocaleString() : "—"}
          subtitle={data?.knowledge_base.rag_enabled ? "RAG enabled ✓" : "RAG disabled"}
          icon={Database}
          loading={loading}
          accent={data?.knowledge_base.rag_enabled ? "text-green-500" : undefined}
        />
        <StatCard
          title="Conversations"
          value={data ? data.conversations.total.toLocaleString() : "—"}
          subtitle="Total sessions (your account)"
          icon={MessageSquare}
          loading={loading}
        />
        <StatCard
          title="Feedback Rating"
          value={data ? `${satisfactionPct}%` : "—"}
          subtitle={
            data
              ? `${data.feedback.positive}/${data.feedback.total} positive`
              : "No feedback yet"
          }
          icon={ThumbsUp}
          loading={loading}
          accent={
            satisfactionPct >= 80
              ? "text-green-500"
              : satisfactionPct >= 60
              ? "text-yellow-500"
              : "text-muted-foreground"
          }
        />
        <StatCard
          title="Learning"
          value={
            data
              ? data.system.learning_active
                ? "Active"
                : "Idle"
              : "—"
          }
          subtitle={data?.system.llm_provider ?? ""}
          icon={Brain}
          loading={loading}
          accent={data?.system.learning_active ? "text-green-500" : undefined}
        />
      </div>

      {/* Info panel when no feedback yet */}
      {!loading && data && data.feedback.total === 0 && (
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle className="text-base">No feedback data yet</CardTitle>
            <CardDescription>
              Charts and satisfaction metrics will appear here after users
              interact with the chat and provide ratings. Start a conversation
              to generate live data.
            </CardDescription>
          </CardHeader>
        </Card>
      )}
    </div>
  );
}