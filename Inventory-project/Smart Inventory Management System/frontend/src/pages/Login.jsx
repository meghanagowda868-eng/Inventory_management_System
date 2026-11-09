import { useState } from 'react';
import { useNavigate, Navigate, Link, useLocation } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const successMessage = location.state?.message || '';

  const { register, handleSubmit, formState: { errors } } = useForm();

  if (isAuthenticated) return <Navigate to="/dashboard" replace />;

  const onSubmit = async (data) => {
    setLoading(true);
    setError('');
    try {
      await login(data.email, data.password);
      navigate('/dashboard');
    } catch (err) {
      setError(
        err.response?.data?.detail ?? 'Login failed. Please check your credentials.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card fade-in">
        <div className="login-brand">
          <div className="login-brand-mark">📊</div>
          <div className="login-brand-copy">
            <h1>Smart Inventory</h1>
            <p>Sign in to your account</p>
          </div>
        </div>

        {successMessage && (
          <div className="auth-alert auth-alert-success">✓ {successMessage}</div>
        )}

        {error && <div className="auth-alert auth-alert-error">⚠ {error}</div>}

        <form className="login-form" onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input
              id="email"
              type="email"
              className="form-input"
              placeholder="maaya@gmail.com"
              {...register('email', {
                required: 'Email is required',
                pattern: { value: /^\S+@\S+$/i, message: 'Invalid email' },
              })}
            />
            {errors.email && <span className="form-error">{errors.email.message}</span>}
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              id="password"
              type="password"
              className="form-input"
              placeholder="••••••••"
              {...register('password', { required: 'Password is required' })}
            />
            {errors.password && <span className="form-error">{errors.password.message}</span>}
          </div>

          <button id="login-submit" type="submit" className="btn btn-primary login-submit" disabled={loading}>
            {loading ? (
              <>
                <span className="spinner" /> Signing in...
              </>
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        <p className="login-footer">
          Don't have an account? <Link to="/register" className="login-link">Create one</Link>
        </p>

        <p className="auth-version">Smart Inventory Management System v1.0</p>
      </div>
    </div>
  );
}
