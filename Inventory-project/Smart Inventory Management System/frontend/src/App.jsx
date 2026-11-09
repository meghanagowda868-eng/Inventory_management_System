import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';

import ProtectedRoute, { RoleRoute } from './components/layout/ProtectedRoute';
import AppShell from './components/layout/AppShell';

import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Inventory from './pages/Inventory';
import ProductDetail from './pages/ProductDetail';
import AddProduct from './pages/AddProduct';
import EditProduct from './pages/EditProduct';
import Reorders from './pages/Reorders';
import PurchaseOrders from './pages/PurchaseOrders';
import Suppliers from './pages/Suppliers';
import AIInsights from './pages/AIInsights';
import Profile from './pages/Profile';
import AdminUsers from './pages/AdminUsers';
import Catalog from './pages/Catalog';
import SeasonalDemand from './pages/SeasonalDemand';
import Offers from './pages/Offers';
import Campaigns from './pages/Campaigns';
import Sales from './pages/Sales';
import Reports from './pages/Reports';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30000,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Protected — wrapped in AppShell */}
            <Route element={<ProtectedRoute />}>
              <Route element={<AppShell />}>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/sales" element={<Sales />} />
                <Route path="/inventory" element={<Inventory />} />
                <Route path="/reorders" element={<Reorders />} />
                <Route path="/purchase-orders" element={<PurchaseOrders />} />
                <Route
                  path="/suppliers"
                  element={
                    <RoleRoute allowedRoles={['admin', 'manager']}>
                      <Suppliers />
                    </RoleRoute>
                  }
                />
                <Route
                  path="/catalog"
                  element={
                    <RoleRoute allowedRoles={['admin', 'manager']}>
                      <Catalog />
                    </RoleRoute>
                  }
                />
                <Route
                  path="/reports"
                  element={
                    <RoleRoute allowedRoles={['admin', 'manager']}>
                      <Reports />
                    </RoleRoute>
                  }
                />
                <Route path="/seasonal-demand" element={<SeasonalDemand />} />
                <Route path="/offers" element={<Offers />} />
                <Route path="/campaigns" element={<Campaigns />} />
                <Route path="/inventory/:id" element={<ProductDetail />} />
                <Route
                  path="/inventory/add"
                  element={
                    <RoleRoute allowedRoles={['admin']}>
                      <AddProduct />
                    </RoleRoute>
                  }
                />
                <Route
                  path="/inventory/:id/edit"
                  element={
                    <RoleRoute allowedRoles={['admin', 'manager']}>
                      <EditProduct />
                    </RoleRoute>
                  }
                />
                <Route path="/ai-insights" element={<AIInsights />} />
                <Route path="/profile" element={<Profile />} />
                <Route
                  path="/admin/users"
                  element={
                    <RoleRoute allowedRoles={['admin']}>
                      <AdminUsers />
                    </RoleRoute>
                  }
                />
              </Route>
            </Route>

            {/* Fallback */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
