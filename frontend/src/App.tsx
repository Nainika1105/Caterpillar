import React from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { FleetProvider } from './context/FleetContext';
import { Navbar } from './components/common/Navbar';
import { AlertBanner } from './components/common/AlertBanner';
import { OperatorDashboard } from './components/operator/OperatorDashboard';
import { AdminDashboard } from './components/admin/AdminDashboard';
import { TrainingDashboard } from './components/training/TrainingDashboard';
import { ErrorBoundary } from './components/common/ErrorBoundary';

const MainView: React.FC = () => {
  const { role } = useAuth();

  return (
    <div className="min-h-screen bg-cat-dark flex flex-col">
      <Navbar />
      <AlertBanner />
      <main className="flex-1 p-3 md:p-5">
        {role === 'operator' && <OperatorDashboard />}
        {role === 'admin' && <AdminDashboard />}
        {role === 'trainer' && <TrainingDashboard />}
      </main>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <FleetProvider>
          <MainView />
        </FleetProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
};

export default App;
