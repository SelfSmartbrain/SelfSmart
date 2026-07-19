import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center space-y-4">
        <h2 className="text-2xl font-bold">Page Not Found</h2>
        <p className="text-muted-foreground">The page you're looking for doesn't exist.</p>
        <Link href="/knowledge" className="px-4 py-2 bg-primary text-primary-foreground rounded-md inline-block">
          Go to Knowledge Hub
        </Link>
      </div>
    </div>
  );
}