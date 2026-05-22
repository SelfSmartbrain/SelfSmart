"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { 
  MessageSquare, 
  BarChart3, 
  Settings, 
  BookOpen, 
  ExternalLink,
  PlusCircle
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useChatStore } from "@/store/useChatStore";

const navItems = [
  { name: "Chat", href: "/", icon: MessageSquare },
  { name: "Dashboard", href: "/dashboard", icon: BarChart3 },
  { name: "Knowledge", href: "/knowledge", icon: BookOpen },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { clearChat } = useChatStore();

  return (
    <div className="flex flex-col w-64 border-r bg-card text-card-foreground">
      <div className="p-6">
        <div className="flex items-center gap-2 mb-8">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-primary-foreground font-bold">
            S
          </div>
          <h1 className="text-xl font-bold tracking-tight">SmartSelf AI</h1>
        </div>

        <Button 
          onClick={clearChat}
          variant="outline" 
          className="w-full justify-start gap-2 mb-6"
        >
          <PlusCircle className="w-4 h-4" />
          New Conversation
        </Button>

        <nav className="space-y-1">
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
                <Icon className="w-4 h-4" />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="mt-auto p-6 border-t">
        <Link
          href="https://github.com/genius-0963/SelfSmart"
          target="_blank"
          className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          <ExternalLink className="w-4 h-4" />
          Documentation
        </Link>
      </div>
    </div>
  );
}
