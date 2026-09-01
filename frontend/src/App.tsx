import React from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { Layout } from "./components/layout/Layout"
import Dashboard from "./pages/Dashboard"

// Placeholder pages
const Placeholder = ({ title }: { title: string }) => (
  <div className="flex h-[80vh] items-center justify-center text-muted-foreground">
    {title} - Coming Soon
  </div>
)

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/forecast" element={<Placeholder title="Forecasting" />} />
          <Route path="/optimize" element={<Placeholder title="Optimization" />} />
          <Route path="/validate" element={<Placeholder title="Queue Validation" />} />
          <Route path="/reports" element={<Placeholder title="Reports" />} />
          <Route path="/settings" element={<Placeholder title="Settings" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
