import { apiUrl } from '@/lib/api';

describe('apiUrl', () => {
  const originalEnv = process.env.NEXT_PUBLIC_API_URL;

  beforeEach(() => {
    delete process.env.NEXT_PUBLIC_API_URL;
  });

  afterAll(() => {
    process.env.NEXT_PUBLIC_API_URL = originalEnv;
  });

  it('returns correct URL with leading slash', () => {
    expect(apiUrl('/api/chat')).toBe('http://localhost:8000/api/chat');
  });

  it('returns correct URL without leading slash', () => {
    expect(apiUrl('api/chat')).toBe('http://localhost:8000/api/chat');
  });

  it('uses NEXT_PUBLIC_API_URL when set', () => {
    process.env.NEXT_PUBLIC_API_URL = 'https://api.example.com';
    expect(apiUrl('/api/chat')).toBe('https://api.example.com/api/chat');
  });
});