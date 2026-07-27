import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AuthWrapper } from '@/components/auth/AuthWrapper';

// Mock the apiUrl function
vi.mock('@/lib/api', () => ({
  apiUrl: (path: string) => `http://localhost:8000${path}`,
}));

// Mock fetch globally
global.fetch = vi.fn();

describe('AuthWrapper', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders login form by default', () => {
    render(<AuthWrapper><div>Protected Content</div></AuthWrapper>);
    
    expect(screen.getByText('Welcome back')).toBeInTheDocument();
    expect(screen.getByLabelText('Email address')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('switches to signup form when toggled', () => {
    render(<AuthWrapper><div>Protected Content</div></AuthWrapper>);
    
    fireEvent.click(screen.getByRole('button', { name: /don't have an account/i }));
    
    expect(screen.getByText('Create an account')).toBeInTheDocument();
    expect(screen.getByLabelText('Full Name')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign up/i })).toBeInTheDocument();
  });

  it('calls login API on form submit', async () => {
    (global.fetch as vi.Mock).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ access_token: 'test-token', token_type: 'bearer' }),
    });

    render(<AuthWrapper><div>Protected Content</div></AuthWrapper>);
    
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'test@example.com' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'SecureP@ss123' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/login',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: 'test@example.com', password: 'SecureP@ss123' }),
        })
      );
    });
  });

  it('shows error on failed login', async () => {
    (global.fetch as vi.Mock).mockResolvedValueOnce({
      ok: false,
      json: () => Promise.resolve({ detail: 'Invalid credentials' }),
    });

    render(<AuthWrapper><div>Protected Content</div></AuthWrapper>);
    
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'test@example.com' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'wrong' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });
  });

  it('shows protected content when token exists', () => {
    localStorage.setItem('token', 'existing-token');
    
    render(<AuthWrapper><div data-testid="protected">Protected Content</div></AuthWrapper>);
    
    expect(screen.getByTestId('protected')).toBeInTheDocument();
    expect(screen.queryByText('Welcome back')).not.toBeInTheDocument();
  });

  it('logs out when logout is triggered', () => {
    localStorage.setItem('token', 'existing-token');
    
    render(<AuthWrapper><div data-testid="protected">Protected Content</div></AuthWrapper>);
    
    window.dispatchEvent(new Event('logout-trigger'));
    
    expect(localStorage.getItem('token')).toBeNull();
  });
});