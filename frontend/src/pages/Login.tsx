import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Shield, Lock, Mail, User as UserIcon, AlertCircle, ArrowRight, Eye, EyeOff } from 'lucide-react';

export const Login: React.FC = () => {
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { login, register, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setLoading(true);

    try {
      if (isRegisterMode) {
        if (!name.trim()) {
          throw new Error('Name is required.');
        }
        if (password.length < 12) {
          throw new Error('Password must be at least 12 characters long.');
        }
        await register(name, email, password);
      } else {
        await login(email, password);
      }
      navigate('/dashboard');
    } catch (err: any) {
      setErrorMsg(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        minHeight: '100vh',
        width: '100vw',
        backgroundColor: 'var(--bg-dark)',
      }}
    >
      {/* Left Branding Panel (Frame 1) */}
      <div
        style={{
          flex: '1 1 50%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '4rem',
          background: 'radial-gradient(circle at 30% 50%, rgba(59, 130, 246, 0.12) 0%, rgba(11, 15, 25, 1) 75%)',
          borderRight: '1px solid var(--border-color)',
          position: 'relative',
        }}
      >
        <div style={{ maxWidth: '460px', textAlign: 'center' }}>
          {/* Glowing AI Emblem */}
          <div
            style={{
              width: '120px',
              height: '120px',
              margin: '0 auto 2.5rem',
              borderRadius: '28px',
              background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, rgba(139, 92, 246, 0.2) 100%)',
              border: '1px solid rgba(59, 130, 246, 0.4)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 40px rgba(59, 130, 246, 0.25)',
            }}
          >
            <Shield size={54} color="#60a5fa" />
            <span style={{ fontSize: '0.85rem', fontWeight: 800, color: '#ffffff', letterSpacing: '0.05em', marginTop: '4px' }}>
              AI
            </span>
          </div>

          <h1 style={{ fontSize: '2.25rem', fontWeight: 800, color: '#ffffff', marginBottom: '0.75rem', letterSpacing: '-0.025em' }}>
            VeraMedia AI
          </h1>
          <p style={{ fontSize: '1.125rem', color: '#93c5fd', fontWeight: 600, marginBottom: '0.5rem' }}>
            Synthetic Content Verification & Forensics Platform
          </p>
          <p style={{ fontSize: '0.95rem', color: 'var(--text-muted)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            Detect. Explain. Protect.
          </p>
        </div>
      </div>

      {/* Right Login/Register Form Card (Frame 1) */}
      <div
        style={{
          flex: '1 1 50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '2rem',
        }}
      >
        <div
          style={{
            width: '100%',
            maxWidth: '440px',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: '16px',
            padding: '2.5rem',
            boxShadow: '0 20px 40px -15px rgba(0, 0, 0, 0.7)',
          }}
        >
          <div style={{ marginBottom: '2rem' }}>
            <h2 style={{ fontSize: '1.625rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.35rem' }}>
              {isRegisterMode ? 'Create Account' : 'Welcome Back!'}
            </h2>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              {isRegisterMode ? 'Register to start forensic media verification' : 'Sign in to access forensic analysis suite'}
            </p>
          </div>

          {errorMsg && (
            <div
              style={{
                backgroundColor: 'rgba(239, 68, 68, 0.12)',
                border: '1px solid rgba(239, 68, 68, 0.35)',
                color: '#fca5a5',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '1.5rem',
              }}
            >
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <span>{errorMsg}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {isRegisterMode && (
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                  Full Name
                </label>
                <div style={{ position: 'relative' }}>
                  <UserIcon size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '13px' }} />
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Alice Analyst"
                    style={{
                      width: '100%',
                      backgroundColor: 'var(--bg-dark)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      padding: '0.65rem 1rem 0.65rem 2.5rem',
                      color: '#ffffff',
                      fontSize: '0.9rem',
                      outline: 'none',
                    }}
                  />
                </div>
              </div>
            )}

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                Email Address
              </label>
              <div style={{ position: 'relative' }}>
                <Mail size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '13px' }} />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="analyst@veramedia.ai"
                  style={{
                    width: '100%',
                    backgroundColor: 'var(--bg-dark)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    padding: '0.65rem 1rem 0.65rem 2.5rem',
                    color: '#ffffff',
                    fontSize: '0.9rem',
                    outline: 'none',
                  }}
                />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                  Password
                </label>
                {!isRegisterMode && (
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }} title="Authentication is managed by local SQLite database. Contact system administrator for password resets.">
                    Self-Hosted Auth
                  </span>
                )}
              </div>
              <div style={{ position: 'relative' }}>
                <Lock size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '13px' }} />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  style={{
                    width: '100%',
                    backgroundColor: 'var(--bg-dark)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    padding: '0.65rem 2.5rem 0.65rem 2.5rem',
                    color: '#ffffff',
                    fontSize: '0.9rem',
                    outline: 'none',
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '12px',
                    top: '12px',
                    background: 'none',
                    border: 'none',
                    color: showPassword ? 'var(--accent-blue)' : 'var(--text-muted)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    padding: 0,
                  }}
                  title={showPassword ? 'Hide password' : 'Show password'}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {isRegisterMode && (
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
                  Must be at least 12 characters long.
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary"
              style={{
                width: '100%',
                padding: '0.75rem',
                fontSize: '0.95rem',
                marginTop: '0.5rem',
              }}
            >
              {loading ? (
                <span>Authenticating...</span>
              ) : (
                <>
                  <span>{isRegisterMode ? 'Register Account' : 'Login'}</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>

          <div style={{ marginTop: '1.75rem', textAlign: 'center', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            {isRegisterMode ? (
              <>
                Already have an account?{' '}
                <button
                  onClick={() => setIsRegisterMode(false)}
                  style={{ background: 'none', border: 'none', color: 'var(--accent-blue)', fontWeight: 600, cursor: 'pointer' }}
                >
                  Sign In
                </button>
              </>
            ) : (
              <>
                Don't have an account?{' '}
                <button
                  onClick={() => setIsRegisterMode(true)}
                  style={{ background: 'none', border: 'none', color: 'var(--accent-blue)', fontWeight: 600, cursor: 'pointer' }}
                >
                  Register
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
