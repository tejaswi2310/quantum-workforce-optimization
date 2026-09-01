import React, { useState, useEffect } from "react"
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card"
import { Badge } from "../components/ui/badge"
import { Button } from "../components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table"
import { 
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ComposedChart, Area
} from "recharts"

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042']

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("analytics")
  const [metrics, setMetrics] = useState<any>(null)
  const [analytics, setAnalytics] = useState<any>(null)
  const [optimization, setOptimization] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true)
        // In a real app we'd handle dynamic project_id
        const projectId = "default"
        
        const [metricsRes, analyticsRes, optRes] = await Promise.all([
          fetch(`/api/v1/projects/${projectId}/dashboard/metrics`),
          fetch(`/api/v1/projects/${projectId}/dashboard/analytics`),
          fetch(`/api/v1/projects/${projectId}/dashboard/optimization`)
        ])
        
        if (!metricsRes.ok || !analyticsRes.ok || !optRes.ok) {
          throw new Error("Failed to load dashboard data. Please ensure the pipeline has been run.")
        }
        
        setMetrics(await metricsRes.json())
        setAnalytics(await analyticsRes.json())
        setOptimization(await optRes.json())
      } catch (err: any) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    
    fetchData()
  }, [])

  const tabs = [
    { id: "analytics", label: "Analytics" },
    { id: "forecasting", label: "Forecasting" },
    { id: "optimization", label: "Optimization" },
    { id: "quantum", label: "Quantum" },
    { id: "impact", label: "Business Impact" },
    { id: "validation", label: "Queue Validation" },
  ]

  if (loading) {
    return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading optimization results...</div>
  }

  if (error || !metrics) {
    return <div className="p-8 text-center text-destructive">{error || "Unable to load optimization results."}</div>
  }

  const mData = metrics.data || {}
  const aData = analytics.data || {}
  const oData = optimization.data || {}

  // Generate basic forecast chart data for visualization based on eval metrics
  // We assume a real API might return the actual forecasted timeseries array.
  const forecastData = [
    { date: "Test Set", predicted: 0, actual: 0 } // Placeholder if not supplied
  ]

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col gap-2">
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">Quantum Workforce Optimizer - Project Overview</p>
      </div>

      <div className="flex space-x-1 rounded-xl bg-muted/50 p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`w-full rounded-lg py-2.5 text-sm font-medium leading-5 ring-white ring-opacity-60 ring-offset-2 ring-offset-primary focus:outline-none focus:ring-2 transition-all ${
              activeTab === tab.id
                ? "bg-background text-foreground shadow"
                : "text-muted-foreground hover:bg-white/[0.12] hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="mt-4">
        {activeTab === "analytics" && (
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
              {[
                { label: "Total Calls", value: (mData.total_calls || 0).toLocaleString() },
                { label: "Avg SLA", value: `${(mData.avg_sla || 0).toFixed(1)}%` },
                { label: "Avg Agents", value: mData.avg_agents },
                { label: "Avg AHT", value: `${mData.avg_handle_time}s` },
                { label: "Peak Hour", value: mData.peak_hour },
              ].map((stat, i) => (
                <Card key={i}>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">{stat.label}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{stat.value}</div>
                  </CardContent>
                </Card>
              ))}
            </div>
            
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
              <Card className="col-span-4">
                <CardHeader>
                  <CardTitle>Calls & Agents per Hour</CardTitle>
                </CardHeader>
                <CardContent className="h-[300px]">
                  {aData.calls_per_hour?.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={aData.calls_per_hour}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="hour" fontSize={12} tickLine={false} axisLine={false} />
                        <YAxis yAxisId="left" fontSize={12} tickLine={false} axisLine={false} />
                        <YAxis yAxisId="right" orientation="right" fontSize={12} tickLine={false} axisLine={false} />
                        <Tooltip />
                        <Legend />
                        <Bar yAxisId="left" dataKey="calls" fill="#8884d8" name="Calls" />
                        <Line yAxisId="right" type="monotone" dataKey="agents" stroke="#ff7300" strokeWidth={3} dot={false} name="Agents" />
                      </ComposedChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex h-full items-center justify-center text-muted-foreground">No data available</div>
                  )}
                </CardContent>
              </Card>
              <Card className="col-span-3">
                <CardHeader>
                  <CardTitle>Calls by Channel</CardTitle>
                </CardHeader>
                <CardContent className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={aData.calls_by_channel || []}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {(aData.calls_by_channel || []).map((entry: any, index: number) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend verticalAlign="bottom" height={36} />
                    </PieChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>
          </div>
        )}

        {activeTab === "forecasting" && (
          <div className="space-y-6">
            <div className="flex gap-4">
              <Badge variant="secondary" className="px-4 py-2 text-sm">
                Test MAE: {aData.forecast_metrics?.mae?.toFixed(2) || 'N/A'}
              </Badge>
              <Badge variant="secondary" className="px-4 py-2 text-sm">
                Test RMSE: {aData.forecast_metrics?.rmse?.toFixed(2) || 'N/A'}
              </Badge>
              <Badge variant="secondary" className="px-4 py-2 text-sm">
                Test sMAPE: {aData.forecast_metrics?.smape?.toFixed(2) || 'N/A'}%
              </Badge>
            </div>
            <Card>
              <CardHeader>
                <CardTitle>Forecast Evaluation (Chronological Test Set)</CardTitle>
              </CardHeader>
              <CardContent className="h-[400px] flex items-center justify-center">
                 <p className="text-muted-foreground">Timeseries forecast visualization requires full chronological arrays.</p>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "optimization" && (
          <div className="space-y-6">
             <Card>
              <CardHeader>
                <CardTitle>Hourly Schedule (OR-Tools CP-SAT)</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Hour</TableHead>
                      <TableHead>Required (Erlang-C)</TableHead>
                      <TableHead>Scheduled</TableHead>
                      <TableHead>Shortfall</TableHead>
                      <TableHead>Coverage Ratio</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(oData.schedule || []).map((row: any) => (
                      <TableRow key={row.hour}>
                        <TableCell>{row.hour}</TableCell>
                        <TableCell>{row.required}</TableCell>
                        <TableCell className="font-semibold text-primary">{row.scheduled}</TableCell>
                        <TableCell className={row.shortfall > 0 ? "text-destructive font-bold" : "text-green-600"}>{row.shortfall}</TableCell>
                        <TableCell>{(row.coverage_ratio * 100).toFixed(1)}%</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "quantum" && (
          <div className="grid gap-6 md:grid-cols-2">
            <Card className="border-primary/50 shadow-primary/20">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-primary animate-pulse"></span>
                  Qiskit QAOA (Quantum)
                </CardTitle>
                <p className="text-xs text-muted-foreground">Quantum Optimization Demonstration — Reduced Problem</p>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-muted-foreground">QUBO Size</span>
                    <span className="font-semibold">{oData.quantum?.qubo_size || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-muted-foreground">Quantum Cost</span>
                    <span className="font-semibold">{oData.quantum?.quantum_cost ? `$${oData.quantum.quantum_cost.toFixed(2)}` : 'N/A'}</span>
                  </div>
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-muted-foreground">Match vs Classical (Reduced Instance)</span>
                    <Badge className="bg-green-500">{oData.quantum?.match_percent ? `${oData.quantum.match_percent}%` : 'N/A'}</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Classical Exact (OR-Tools)</CardTitle>
                <p className="text-xs text-muted-foreground">Same Reduced Instance</p>
              </CardHeader>
              <CardContent>
                 <div className="space-y-4">
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-muted-foreground">Classical Cost</span>
                    <span className="font-semibold">{oData.quantum?.classical_cost ? `$${oData.quantum.classical_cost.toFixed(2)}` : 'N/A'}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "impact" && (
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Actual Optimized Cost</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-green-500">${(oData.total_cost || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Total Scheduled Agents (Unique)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{mData.total_agents || 0}</div>
                </CardContent>
              </Card>
            </div>
            <div className="flex justify-end">
              <Button>Download TXT Report</Button>
            </div>
          </div>
        )}

        {activeTab === "validation" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium">Analytical Erlang-C Queue Validation</h3>
              <Badge className="bg-green-500 px-4 py-1 text-sm">{mData.min_sla >= 80 ? "PASS" : "FAIL (SLA Breach)"}</Badge>
            </div>
            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Hour</TableHead>
                      <TableHead>Calls</TableHead>
                      <TableHead>Agents</TableHead>
                      <TableHead>SLA %</TableHead>
                      <TableHead>ASA (sec)</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(aData.calls_per_hour || []).map((row: any) => (
                      <TableRow key={row.hour}>
                        <TableCell>{row.hour}:00</TableCell>
                        <TableCell>{Math.round(row.calls)}</TableCell>
                        <TableCell>{row.agents}</TableCell>
                        <TableCell className="font-semibold text-green-600">{(row.sla).toFixed(1)}%</TableCell>
                        <TableCell>{row.asa || 0}</TableCell>
                        <TableCell><Badge className={row.sla >= 80 ? "bg-green-500/20 text-green-700" : "bg-red-500/20 text-red-700"}>{row.sla >= 80 ? 'PASS' : 'FAIL'}</Badge></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}
