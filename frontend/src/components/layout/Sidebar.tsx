import React from "react"
import { Link, useLocation } from "react-router-dom"
import { LayoutDashboard, TrendingUp, Settings, BarChart2, ShieldCheck, PlayCircle, Zap } from "lucide-react"
import { cn } from "../../lib/utils"

const navigation = [
  { name: "Analytics", href: "/dashboard", icon: LayoutDashboard },
  { name: "Forecasting", href: "/forecast", icon: TrendingUp },
  { name: "Optimization", href: "/optimize", icon: Zap },
  { name: "Queue Validation", href: "/validate", icon: ShieldCheck },
  { name: "Reports", href: "/reports", icon: BarChart2 },
  { name: "Settings", href: "/settings", icon: Settings },
]

export function Sidebar() {
  const location = useLocation()

  return (
    <div className="flex h-full w-64 flex-col bg-card border-r shadow-sm">
      <div className="flex h-16 shrink-0 items-center px-6">
        <PlayCircle className="h-8 w-8 text-primary" />
        <span className="ml-3 text-lg font-bold tracking-tight text-foreground">Quantum WFO</span>
      </div>
      <nav className="flex flex-1 flex-col overflow-y-auto p-4 space-y-1">
        {navigation.map((item) => {
          const isActive = location.pathname.startsWith(item.href)
          return (
            <Link
              key={item.name}
              to={item.href}
              className={cn(
                "group flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <item.icon
                className={cn(
                  "mr-3 h-5 w-5 shrink-0",
                  isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground"
                )}
                aria-hidden="true"
              />
              {item.name}
            </Link>
          )
        })}
      </nav>
      <div className="p-4 border-t">
        <div className="flex items-center">
          <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold">
            A
          </div>
          <div className="ml-3">
            <p className="text-sm font-medium text-foreground">Admin User</p>
            <p className="text-xs text-muted-foreground">admin@vanguard.com</p>
          </div>
        </div>
      </div>
    </div>
  )
}
