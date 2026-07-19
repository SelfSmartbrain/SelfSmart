"use client";

import dynamic from 'next/dynamic';

const KnowledgeContent = dynamic(() => import('./KnowledgeContent'), {
  loading: () => (
    <div className="flex min-h-screen items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
    </div>
  ),
});

export default function KnowledgePage() {
  return <KnowledgeContent />;
}