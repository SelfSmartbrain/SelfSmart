"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import {
  MessageSquare,
  BarChart3,
  Settings,
  BookOpen,
  ExternalLink,
  PlusCircle,
  Trash2,
  User,
  LogOut,
  Activity,
  Clock
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useChatStore } from "@/store/useChatStore";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

const navItems = [
  { name: "Chat", href: "/", icon: MessageSquare },
  { name: "Dashboard", href: "/dashboard", icon: BarChart3 },
  { name: "Knowledge", href: "/knowledge", icon: BookOpen },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const [userName, setUserName] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("userName");
    }
    return null;
  });
  const {
    clearChat,
    conversations,
    conversationId,
    fetchConversations,
    selectConversation,
    deleteConversation
  } = useChatStore();

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("userName");
    window.dispatchEvent(new Event("logout-trigger"));
    window.location.href = "/";
  };

  const getUserInitials = () => {
    if (!userName) return "U";
    return userName
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <div className="flex flex-col w-64 border-r bg-card text-card-foreground h-full overflow-hidden">
      <div className="p-4 flex flex-col flex-1 min-h-0 overflow-hidden">
        <div className="flex items-center gap-2 mb-6">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-primary-foreground font-bold shrink-0">
            S
          </div>
          <h1 className="text-xl font-bold tracking-tight truncate">SmartSelf AI</h1>
        </div>

        <Button
          onClick={clearChat}
          variant="outline"
          className="w-full justify-start gap-2 mb-4 shrink-0"
        >
          <PlusCircle className="w-4 h-4" />
          New Conversation
        </Button>

        <nav className="space-y-1 mb-4 shrink-0">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <Icon className="w-4 h-4 shrink-0" />
                {item.name}
              </Link>
            );
          })}
        </nav>

        <hr className="border-border my-2 shrink-0" />

        {/* Recent Chats Section */}
        <div className="flex-1 min-h-0 flex flex-col overflow-hidden mt-2">
          <div className="px-3 mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider shrink-0">
            Recent Chats
          </div>
          <ScrollArea className="flex-1">
            <div className="space-y-1 px-1 pb-4">
              {conversations.length === 0 ? (
                <div className="px-3 py-2 text-xs text-muted-foreground italic text-center">
                  No conversations yet
                </div>
              ) : (
                conversations.map((conv) => {
                  const isActive = conversationId === conv.id;
                  return (
                    <div
                      key={conv.id}
                      className={cn(
                        "group flex items-center justify-between px-3 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer",
                        isActive
                          ? "bg-accent text-accent-foreground font-semibold"
                          : "hover:bg-accent/50 hover:text-accent-foreground"
                      )}
                      onClick={() => selectConversation(conv.id)}
                    >
                      <span className="truncate flex-1 pr-2">{conv.title || "Untitled Chat"}</span>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 opacity-0 group-hover:opacity-100 hover:text-red-500 hover:bg-transparent transition-opacity shrink-0"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteConversation(conv.id);
                        }}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  );
                })
              )}
            </div>
          </ScrollArea>
        </div>
      </div>

      <div className="mt-auto p-4 border-t flex flex-col gap-2 shrink-0 bg-muted/20">
        {/* User Profile Section */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className="w-full justify-start gap-3 px-3 h-auto py-2"
            >
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-primary text-primary-foreground text-xs font-semibold">
                  {getUserInitials()}
                </AvatarFallback>
              </Avatar>
              <div className="flex flex-col items-start flex-1">
                <span className="text-sm font-medium truncate">
                  {userName || "User"}
                </span>
                <span className="text-xs text-muted-foreground">Signed in</span>
              </div>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuItem className="cursor-pointer" onClick={handleLogout}>
              <LogOut className="mr-2 h-4 w-4" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Activity Section */}
        <div className="px-3 py-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
            <Activity className="w-3 h-3" />
            Activity
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Clock className="w-3 h-3" />
              <span>{conversations.length} conversations</span>
            </div>
          </div>
        </div>

        <Link
          href="https://github.com/genius-0963/SelfSmart"
          target="_blank"
          className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          <ExternalLink className="w-4 h-4 shrink-0" />
          Documentation
        </Link>
      </div>
    </div>
  );
}
