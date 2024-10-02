"use client"

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  AlertTriangle,
  CheckCircle,
  Activity,
  Settings,
  Moon,
  Sun,
} from 'lucide-react'

// Define types
type StatusType = 'no issues' | 'notice' | 'incident' | 'outage' | 'failure'

interface ServiceStatus {
  overall: StatusType
  [key: string]: StatusType
}

interface Event {
  timestamp: string
  message: string
}

interface SystemStatus {
  [service: string]: ServiceStatus
}

interface LastLogMessages {
  [service: string]: string
}

interface Timeline {
  [service: string]: Event[]
}

interface UpdateData {
  source: string
  status_type: StatusType
  message?: string
}

// Constants
const API_BASE_URL = "http://localhost:8000"  // Adjust as needed
const SERVICES = ['airflow', 'dbt', 'database', 'ci']

const Dashboard: React.FC = () => {
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({})
  const [lastLogMessages, setLastLogMessages] = useState<LastLogMessages>({})
  const [timelines, setTimelines] = useState<Timeline>({})
  const [isDarkMode, setIsDarkMode] = useState(false)

  useEffect(() => {
    document.body.classList.toggle('dark', isDarkMode)
  }, [isDarkMode])

  useEffect(() => {
    // Initialize system status
    const initialStatus: SystemStatus = {}
    SERVICES.forEach(service => {
      initialStatus[service] = { overall: 'no issues' }
    })
    setSystemStatus(initialStatus)

    // Set up SSE connection
    const eventSource = new EventSource(`${API_BASE_URL}/sse`)

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)
      processUpdate(data)
    }

    eventSource.onerror = (error) => {
      console.error('SSE Error:', error)
      eventSource.close()
    }

    return () => {
      eventSource.close()
    }
  }, [])

  const processUpdate = (update: UpdateData) => {
    if ('source' in update && 'status_type' in update) {
      const { source, status_type, message } = update
      const service = SERVICES.find(s => source.startsWith(s)) || source
      const component = source.replace(`${service}_`, '')

      setSystemStatus(prevStatus => {
        const newStatus = { ...prevStatus }
        if (!newStatus[service]) newStatus[service] = { overall: 'no issues' }
        if (component) {
          newStatus[service][component] = status_type
        } else {
          newStatus[service].overall = status_type
        }
        return newStatus
      })

      setLastLogMessages(prevMessages => ({
        ...prevMessages,
        [service]: message || ''
      }))

      setTimelines(prevTimelines => {
        const newTimelines = { ...prevTimelines }
        if (!newTimelines[service]) newTimelines[service] = []
        newTimelines[service].push({
          timestamp: new Date().toISOString(),
          message: message || ''
        })
        return newTimelines
      })
    }
  }

  const getStatusIconAndColor = (status: StatusType): [React.ReactNode, string] => {
    switch (status) {
      case 'no issues':
        return [<CheckCircle key="check" className="h-5 w-5" />, 'text-green-500']
      case 'notice':
        return [<AlertTriangle key="notice" className="h-5 w-5" />, 'text-yellow-500']
      case 'incident':
        return [<Activity key="incident" className="h-5 w-5" />, 'text-orange-500']
      case 'outage':
      case 'failure':
        return [<AlertTriangle key="failure" className="h-5 w-5" />, 'text-red-500']
      default:
        return [<Activity key="default" className="h-5 w-5" />, 'text-blue-500']
    }
  }

  const getOverallStatus = (): StatusType => {
    const statuses = Object.values(systemStatus).map(s => s.overall)
    if (statuses.includes('outage') || statuses.includes('failure')) return 'outage'
    if (statuses.includes('incident')) return 'incident'
    if (statuses.includes('notice')) return 'notice'
    return 'no issues'
  }

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">Pylot Light Status Page</h1>
          <div className="flex items-center space-x-4">
            <Button variant="outline" size="icon" onClick={() => setIsDarkMode(!isDarkMode)}>
              {isDarkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              <span className="sr-only">Toggle dark mode</span>
            </Button>
            <Button variant="outline" size="icon">
              <Settings className="h-4 w-4" />
              <span className="sr-only">Settings</span>
            </Button>
          </div>
        </div>

        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Overall Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold flex items-center">
              {getStatusIconAndColor(getOverallStatus())[0]}
              <span className="ml-2">{getOverallStatus()}</span>
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {SERVICES.map((service) => (
            <Card key={service} className="overflow-hidden transition-shadow hover:shadow-lg">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xl font-bold">{service.toUpperCase()}</CardTitle>
                {getStatusIconAndColor(systemStatus[service]?.overall || 'no issues')[0]}
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(systemStatus[service] || {}).map(([component, status]) => (
                    <div key={component} className="flex justify-between items-center">
                      <span className="capitalize">{component}</span>
                      <span className={getStatusIconAndColor(status)[1]}>{status}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-4">
                  <h4 className="font-semibold mb-2">Recent Events:</h4>
                  <ScrollArea className="h-[100px]">
                    {timelines[service]?.slice(-5).map((event, index) => (
                      <p key={`${service}-event-${index}`} className="text-sm mb-1">
                        {new Date(event.timestamp).toLocaleTimeString()}: {event.message}
                      </p>
                    ))}
                  </ScrollArea>
                </div>
                <div className="mt-4">
                  <h4 className="font-semibold mb-2">Last Message:</h4>
                  <p className="text-sm">{lastLogMessages[service] || 'No messages'}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Status Legend</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-between">
            <div key="no-issues">✓ No Issues</div>
            <div key="maintenance">🔧 Maintenance</div>
            <div key="notice">🚩 Notice</div>
            <div key="incident">⚠️ Incident</div>
            <div key="outage">🔴 Outage/Failure</div>
          </CardContent>
        </Card>

        <div className="mt-8 text-center">
          <p>Having trouble? <a href="https://pylotlight.com/troubleshoot" className="text-blue-500 hover:underline">Troubleshoot connection issues</a> or email us at support@pylotlight.com</p>
        </div>
      </div>
    </div>
  )
}

export default Dashboard