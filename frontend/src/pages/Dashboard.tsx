import React, { useState } from "react"
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

  const tabs = [
    { id: "analytics", label: "Analytics" },
    { id: "forecasting", label: "Forecasting" },
    { id: "optimization", label: "Optimization" },
    { id: "quantum", label: "Quantum" },
    { id: "impact", label: "Business Impact" },
    { id: "validation", label: "Queue Validation" },
  ]

  // Dummy Data for charts
  const hourlyData = Array.from({ length: 24 }).map((_, i) => ({
    hour: `${i}:00`,
    calls: Math.floor(Math.random() * 800) + 50,
  }))
  
  const pieData = [
    { name: 'Voice', value: 60 },
    { name: 'Chat', value: 30 },
    { name: 'Email', value: 10 },
  ]
  
  const forecastData = Array.from({ length: 7 }).map((_, i) => {
    const base = Math.floor(Math.random() * 5000) + 3000
    return {
      date: `2026-08-0${i + 1}`,
      predicted: base,
      lower: base * 0.9,
      upper: base * 1.1,
    }
  })

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
                { label: "Total Calls", value: "51,240" },
                { label: "Avg SLA", value: "82.5%" },
                { label: "Avg Agents", value: "58" },
                { label: "Avg AHT", value: "240s" },
                { label: "Peak Hour", value: "10:00 AM" },
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
                  <CardTitle>Calls per Hour</CardTitle>
                </CardHeader>
                <CardContent className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={hourlyData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="hour" fontSize={12} tickLine={false} axisLine={false} />
                      <YAxis fontSize={12} tickLine={false} axisLine={false} />
                      <Tooltip />
                      <Line type="monotone" dataKey="calls" stroke="#8884d8" strokeWidth={3} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
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
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {pieData.map((entry, index) => (
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
              <Badge variant="secondary" className="px-4 py-2 text-sm">MAE: 6.44</Badge>
              <Badge variant="secondary" className="px-4 py-2 text-sm">RMSE: 9.97</Badge>
              <Badge variant="secondary" className="px-4 py-2 text-sm">R²: 0.86</Badge>
            </div>
            <Card>
              <CardHeader>
                <CardTitle>7-Day Demand Forecast</CardTitle>
              </CardHeader>
              <CardContent className="h-[400px]">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={forecastData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Area type="monotone" dataKey="upper" fill="#82ca9d" stroke="none" fillOpacity={0.3} />
                    <Area type="monotone" dataKey="lower" fill="#fff" stroke="none" />
                    <Line type="monotone" dataKey="predicted" stroke="#8884d8" strokeWidth={3} />
                  </ComposedChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "optimization" && (
          <div className="space-y-6">
             <Card>
              <CardHeader>
                <CardTitle>Hourly Schedule (OR-Tools)</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Hour</TableHead>
                      <TableHead>Required</TableHead>
                      <TableHead>Scheduled</TableHead>
                      <TableHead>Cost</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {[9,10,11,12].map(h => (
                      <TableRow key={h}>
                        <TableCell>{h}:00</TableCell>
                        <TableCell>42</TableCell>
                        <TableCell className="font-semibold text-primary">58</TableCell>
                        <TableCell>$870.00</TableCell>
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
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-muted-foreground">QUBO Size</span>
                    <span className="font-semibold">8x8</span>
                  </div>
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-muted-foreground">Cost</span>
                    <span className="font-semibold">$870</span>
                  </div>
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-muted-foreground">Match vs Classical</span>
                    <Badge className="bg-green-500">100%</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Classical Exact (OR-Tools)</CardTitle>
              </CardHeader>
              <CardContent>
                 <div className="space-y-4">
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-muted-foreground">Constraints</span>
                    <span className="font-semibold">124</span>
                  </div>
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-muted-foreground">Cost</span>
                    <span className="font-semibold">$870</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "impact" && (
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Naive Cost</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-destructive">$1,440</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Optimized Cost</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-green-500">$870</div>
                </CardContent>
              </Card>
              <Card className="bg-primary text-primary-foreground">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-primary-foreground/80">Annual Savings</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-4xl font-bold">$208,050</div>
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
              <h3 className="text-lg font-medium">Erlang C Simulation</h3>
              <Badge className="bg-green-500 px-4 py-1 text-sm">24/24 Hours PASS</Badge>
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
                    {[9,10,11].map(h => (
                      <TableRow key={h}>
                        <TableCell>{h}:00</TableCell>
                        <TableCell>420</TableCell>
                        <TableCell>58</TableCell>
                        <TableCell className="font-semibold text-green-600">89.4%</TableCell>
                        <TableCell>12.4</TableCell>
                        <TableCell><Badge className="bg-green-500/20 text-green-700 hover:bg-green-500/30">PASS</Badge></TableCell>
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
