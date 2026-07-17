'use client';

import { useEffect } from 'react';

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => { console.error(error); }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center space-y-4">
        <h2 className="text-2xl font-bold">Something went wrong</h2>
        <p className="text-muted-foreground">An unexpected error occurred.</p>
        <button onClick={reset} className="px-4 py-2 bg-primary text-primary-foreground rounded-md">
          Try Again
        </button>
      </div>
    </div>
  );
}
