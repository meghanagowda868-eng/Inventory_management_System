import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { authApi } from '../api/authApi';
import { useAuth } from '../context/AuthContext';

export default function Profile() {
  const { user, updateUser } = useAuth();
  const qc = useQueryClient();
  const [tab, setTab] = useState('profile');
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const { register: rProfile, handleSubmit: hsProfile, formState: { errors: eProfile, isDirty: dirtyProfile } } = useForm({
    values: { name: user?.name ?? '', email: user?.email ?? '' },
  });

  const { register: rPwd, handleSubmit: hsPwd, reset: resetPwd, formState: { errors: ePwd } } = useForm();

  const profileMutation = useMutation({
    mutationFn: (data) => authApi.updateProfile(data),
    onSuccess: ({ data }) => {
      updateUser(data);
      setSuccessMsg('Profile updated successfully');
      setErrorMsg('');
      setTimeout(() => setSuccessMsg(''), 3000);
    },
    onError: (err) => setErrorMsg(err.response?.data?.detail ?? 'Update failed'),
  });

  const pwdMutation = useMutation({
    mutationFn: (data) => authApi.changePassword(data),
    onSuccess: () => {
      setSuccessMsg('Password changed. Please log in again with your new password.');
      setErrorMsg('');
      resetPwd();
    },
    onError: (err) => setErrorMsg(err.response?.data?.detail ?? 'Password change failed'),
  });

  const TABS = ['profile', 'security'];

  return (
    <div className="page-content fade-in" style={{ maxWidth: 640 }}>
      <div className="page-header">
        <h1 className="page-title">My Profile</h1>
        <p className="page-subtitle">Manage your account settings</p>
      </div>

      {/* Avatar card */}
      <div className="card p-6" style={{ marginBottom: 24, display: 'flex', alignItems: 'center', gap: 20 }}>
        <div style={{
          width: 72, height: 72,
          background: 'linear-gradient(135deg, var(--color-accent), var(--color-accent-dark))',
          borderRadius: '50%',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 28, fontWeight: 800,
        }}>
          {user?.name?.[0]?.toUpperCase()}
        </div>
        <div>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{user?.name}</div>
          <div style={{ color: 'var(--color-text-muted)', fontSize: 14 }}>{user?.email}</div>
          <span className="badge badge-info" style={{ marginTop: 6, textTransform: 'capitalize' }}>
            {user?.role}
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex-center gap-2" style={{ marginBottom: 24, justifyContent: 'flex-start' }}>
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => { setTab(t); setSuccessMsg(''); setErrorMsg(''); }}
            className={`btn btn-sm ${tab === t ? 'btn-primary' : 'btn-secondary'}`}
            style={{ textTransform: 'capitalize' }}
          >
            {t === 'profile' ? '👤 Profile' : '🔒 Security'}
          </button>
        ))}
      </div>

      {/* Messages */}
      {successMsg && (
        <div style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)', borderRadius: 'var(--radius-md)', padding: '12px 16px', fontSize: 14, color: 'var(--color-success)', marginBottom: 16 }}>
          ✓ {successMsg}
        </div>
      )}
      {errorMsg && (
        <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 'var(--radius-md)', padding: '12px 16px', fontSize: 14, color: 'var(--color-danger)', marginBottom: 16 }}>
          ⚠ {errorMsg}
        </div>
      )}

      {/* Profile Tab */}
      {tab === 'profile' && (
        <div className="card p-6">
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>Update Profile</h2>
          <form onSubmit={hsProfile((data) => profileMutation.mutate(data))} noValidate>
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input className="form-input" {...rProfile('name', { required: 'Name is required', minLength: { value: 2, message: 'Min 2 chars' } })} />
              {eProfile.name && <span className="form-error">{eProfile.name.message}</span>}
            </div>
            <div className="form-group">
              <label className="form-label">Email Address</label>
              <input type="email" className="form-input"
                {...rProfile('email', { required: 'Email is required', pattern: { value: /^\S+@\S+$/i, message: 'Invalid email' } })} />
              {eProfile.email && <span className="form-error">{eProfile.email.message}</span>}
            </div>
            <button type="submit" className="btn btn-primary" disabled={profileMutation.isPending || !dirtyProfile}>
              {profileMutation.isPending ? 'Saving...' : '✓ Save Changes'}
            </button>
          </form>
        </div>
      )}

      {/* Security Tab */}
      {tab === 'security' && (
        <div className="card p-6">
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>Change Password</h2>
          <form onSubmit={hsPwd((data) => pwdMutation.mutate(data))} noValidate>
            <div className="form-group">
              <label className="form-label">Current Password</label>
              <input type="password" className="form-input" {...rPwd('current_password', { required: 'Required' })} />
              {ePwd.current_password && <span className="form-error">{ePwd.current_password.message}</span>}
            </div>
            <div className="form-group">
              <label className="form-label">New Password</label>
              <input type="password" className="form-input"
                {...rPwd('new_password', {
                  required: 'Required',
                  minLength: { value: 8, message: 'Min 8 characters' },
                  validate: {
                    hasUpper: v => /[A-Z]/.test(v) || 'Needs uppercase letter',
                    hasDigit: v => /\d/.test(v) || 'Needs a digit',
                  },
                })}
              />
              {ePwd.new_password && <span className="form-error">{ePwd.new_password.message}</span>}
            </div>
            <button type="submit" className="btn btn-primary" disabled={pwdMutation.isPending}>
              {pwdMutation.isPending ? 'Changing...' : '🔒 Change Password'}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
