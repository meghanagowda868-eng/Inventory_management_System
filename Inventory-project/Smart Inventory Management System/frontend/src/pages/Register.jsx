import { useState } from 'react';
import { useNavigate, Link, Navigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useAuth } from '../context/AuthContext';
import { authApi } from '../api/authApi';

export default function Register() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm();

  if (isAuthenticated) return <Navigate to="/dashboard" replace />;

  const onSubmit = async (data) => {
    setLoading(true);
    setError('');
    try {
      await authApi.register({
        name: data.name,
        email: data.email,
        password: data.password,
      });
      // Auto-login after registration
      navigate('/login', {
        state: { message: 'Account created! Please sign in.' },
      });
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail.map((d) => d.msg).join(', '));
      } else {
        setError(detail ?? 'Registration failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card fade-in auth-card-register">
        <div className="login-brand">
          <div className="login-brand-mark">📊</div>
          <div className="login-brand-copy">
            <h1>Create Account</h1>
            <p>Join Smart Inventory Management</p>
          </div>
        </div>

        {error && <div className="auth-alert auth-alert-error">⚠ {error}</div>}

        <form className="login-form" onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className="form-group">
            <label className="form-label">Full Name</label>
            <input
              id="name"
              type="text"
              className="form-input"
              placeholder="John Doe"
              {...register('name', {
                required: 'Full name is required',
                minLength: { value: 2, message: 'Name must be at least 2 characters' },
              })}
            />
            {errors.name && <span className="form-error">{errors.name.message}</span>}
          </div>

          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input
              id="email"
              type="email"
              className="form-input"
              placeholder="john@example.com"
              {...register('email', {
                required: 'Email is required',
                pattern: { value: /^\S+@\S+$/i, message: 'Invalid email address' },
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
              placeholder="Min 8 chars, 1 uppercase, 1 digit"
              {...register('password', {
                required: 'Password is required',
                minLength: { value: 8, message: 'Password must be at least 8 characters' },
                validate: {
                  hasUpper: (v) =>
                    /[A-Z]/.test(v) || 'Password must contain at least one uppercase letter',
                  hasDigit: (v) =>
                    /[0-9]/.test(v) || 'Password must contain at least one digit',
                },
              })}
            />
            {errors.password && <span className="form-error">{errors.password.message}</span>}
          </div>

          <button id="register-submit" type="submit" className="btn btn-primary login-submit" disabled={loading}>
            {loading ? (
              <>
                <span className="spinner" /> Creating account...
              </>
            ) : (
              'Create Account'
            )}
          </button>
        </form>

        <p className="login-footer">
          Already have an account? <Link to="/login" className="login-link">Sign In</Link>
        </p>
      </div>
    </div>
  );
}
