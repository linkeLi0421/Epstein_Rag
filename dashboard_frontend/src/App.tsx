import { Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";
import Layout from "./components/Layout";
import ErrorBoundary from "./components/ErrorBoundary";
import Dashboard from "./pages/Dashboard";
import Analytics from "./pages/Analytics";
import Queries from "./pages/Queries";
import Jobs from "./pages/Jobs";
import Search from "./pages/Search";
import Settings from "./pages/Settings";
import { dashboardWs } from "./lib/websocket";

export default function App() {
  useEffect(() => {
    dashboardWs.connect();
    return () => dashboardWs.disconnect();
  }, []);

  return (
    <ErrorBoundary>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
          <Route path="/analytics" element={<ErrorBoundary><Analytics /></ErrorBoundary>} />
          <Route path="/queries" element={<ErrorBoundary><Queries /></ErrorBoundary>} />
          <Route path="/jobs" element={<ErrorBoundary><Jobs /></ErrorBoundary>} />
          <Route path="/search" element={<ErrorBoundary><Search /></ErrorBoundary>} />
          <Route path="/settings" element={<ErrorBoundary><Settings /></ErrorBoundary>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </ErrorBoundary>
  );
}
