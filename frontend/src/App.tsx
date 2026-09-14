import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AppLayout } from './components/layout/AppLayout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Analyze } from './pages/Analyze';
import { Investigations } from './pages/Investigations';
import { DetectionHistory } from './pages/DetectionHistory';
import { EvidenceVault } from './pages/EvidenceVault';
import { ReportGeneration } from './pages/ReportGeneration';
import { AbuseDispatcher } from './pages/AbuseDispatcher';
import { Settings } from './pages/Settings';
import { SystemHealth } from './pages/SystemHealth';

const RequireAuth: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#0b0f19', color: '#ffffff' }}>
        Loading VeraMedia Forensics Console...
      </div>
    );
  }

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Route (Frame 1) */}
          <Route path="/login" element={<Login />} />

          {/* Protected Authenticated Routes (Frames 2-20) */}
          <Route
            element={
              <RequireAuth>
                <AppLayout />
              </RequireAuth>
            }
          >
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/analyze" element={<Analyze />} />
            <Route path="/investigations" element={<Investigations />} />
            <Route path="/history" element={<DetectionHistory />} />
            <Route path="/vault" element={<EvidenceVault />} />
            <Route path="/reports" element={<ReportGeneration />} />
            <Route path="/abuse" element={<AbuseDispatcher />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/health" element={<SystemHealth />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};
