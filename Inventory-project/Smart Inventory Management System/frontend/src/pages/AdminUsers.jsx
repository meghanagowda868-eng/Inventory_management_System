import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Navigate } from 'react-router-dom';
import { authApi } from '../api/authApi';
import { useAuth } from '../context/AuthContext';

const ROLE_OPTIONS = [
  { value: 'employee', label: 'Employee' },
  { value: 'manager', label: 'Manager' },
  { value: 'admin', label: 'Admin' },
];

export default function AdminUsers() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [editingId, setEditingId] = useState(null);
  const [createForm, setCreateForm] = useState({ name: '', email: '', password: '', role: 'employee' });
  const [editForm, setEditForm] = useState({ name: '', email: '', role: 'employee', is_active: true });

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => authApi.getUsers().then((res) => res.data),
    staleTime: 30000,
  });

  const updateRoleMutation = useMutation({
    mutationFn: ({ userId, role }) => authApi.updateUserRole(userId, { role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  });

  const createMutation = useMutation({
    mutationFn: (data) => authApi.createUser(data),
    onSuccess: () => {
      setCreateForm({ name: '', email: '', password: '', role: 'employee' });
      qc.invalidateQueries({ queryKey: ['admin-users'] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ userId, data }) => authApi.updateUser(userId, data),
    onSuccess: () => {
      setEditingId(null);
      qc.invalidateQueries({ queryKey: ['admin-users'] });
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({ userId, isActive }) => authApi.updateUser(userId, { is_active: isActive }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (userId) => authApi.deleteUser(userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  });

  if (user?.role !== 'admin') {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="page-content fade-in">
      <div className="page-header inventory-header">
        <div>
          <h1 className="page-title">User Access Control</h1>
          <p className="page-subtitle">Manage admin, manager, and employee access across the platform.</p>
        </div>
      </div>

      <form
        className="card p-6"
        style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: 12, marginBottom: 24, alignItems: 'end' }}
        onSubmit={(event) => { event.preventDefault(); createMutation.mutate(createForm); }}
      >
        <div className="form-group"><label className="form-label">Name</label><input className="form-input" required value={createForm.name} onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })} /></div>
        <div className="form-group"><label className="form-label">Email</label><input className="form-input" type="email" required value={createForm.email} onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })} /></div>
        <div className="form-group"><label className="form-label">Temporary Password</label><input className="form-input" type="password" required minLength={8} value={createForm.password} onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })} /></div>
        <div className="form-group"><label className="form-label">Role</label><select className="form-select" value={createForm.role} onChange={(e) => setCreateForm({ ...createForm, role: e.target.value })}>{ROLE_OPTIONS.map((role) => <option key={role.value} value={role.value}>{role.label}</option>)}</select><button className="btn btn-primary" type="submit" disabled={createMutation.isPending} style={{ marginTop: 10 }}>{createMutation.isPending ? 'Adding...' : '+ Add User'}</button></div>
      </form>

      <div className="card inventory-table-card">
        {isLoading ? (
          <div className="flex-center loader-box">
            <div className="spinner spinner-lg" />
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((item) => (
                  <tr key={item.id}>
                    <td className="bold-cell">{item.name}</td>
                    <td className="muted-cell">{item.email}</td>
                    <td>
                      <span className={`badge ${item.role === 'admin' ? 'badge-info' : item.role === 'manager' ? 'badge-warning' : 'badge-neutral'}`}>
                        {item.role}
                      </span>
                    </td>
                    <td>
                      <span className={item.is_active ? 'text-success' : 'text-danger'}>
                        {item.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>
                      <div className="action-group">
                        {editingId === item.id ? (
                          <>
                            <input className="form-input" value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} aria-label="Edit name" />
                            <input className="form-input" type="email" value={editForm.email} onChange={(e) => setEditForm({ ...editForm, email: e.target.value })} aria-label="Edit email" />
                            <select className="form-select" value={editForm.role} onChange={(e) => setEditForm({ ...editForm, role: e.target.value })} aria-label="Edit role">{ROLE_OPTIONS.map((role) => <option key={role.value} value={role.value}>{role.label}</option>)}</select>
                            <button className="btn btn-primary btn-sm" onClick={() => updateMutation.mutate({ userId: item.id, data: editForm })} disabled={updateMutation.isPending}>Save</button>
                            <button className="btn btn-secondary btn-sm" onClick={() => setEditingId(null)}>Cancel</button>
                          </>
                        ) : (
                          <>
                        <select
                          className="form-select"
                          style={{ minWidth: 120 }}
                          value={item.role}
                          disabled={item.id === user.id || updateRoleMutation.isPending}
                          onChange={(e) => updateRoleMutation.mutate({ userId: item.id, role: e.target.value })}
                        >
                          {ROLE_OPTIONS.map((role) => (
                            <option key={role.value} value={role.value}>
                              {role.label}
                            </option>
                          ))}
                        </select>
                            <button className="btn btn-secondary btn-sm" onClick={() => { setEditingId(item.id); setEditForm({ name: item.name, email: item.email, role: item.role, is_active: item.is_active }); }}>Edit</button>
                            {item.id !== user.id && (
                              <button className="btn btn-secondary btn-sm" onClick={() => statusMutation.mutate({ userId: item.id, isActive: !item.is_active })} disabled={statusMutation.isPending}>
                                {item.is_active ? 'Deactivate' : 'Activate'}
                              </button>
                            )}
                            {item.id !== user.id && (
                              <button className="btn btn-secondary btn-sm" onClick={() => { if (window.confirm(`Permanently delete ${item.name}? This cannot be undone.`)) deleteMutation.mutate(item.id); }} disabled={deleteMutation.isPending}>
                                Delete
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
