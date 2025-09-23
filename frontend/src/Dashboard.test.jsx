import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import Dashboard from './Dashboard'

// Mock WebSocket
global.WebSocket = vi.fn().mockImplementation(() => ({
  close: vi.fn(),
  send: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  readyState: 1, // OPEN
}))

// Mock fetch globally
global.fetch = vi.fn()

describe('Dashboard Component', () => {
  beforeEach(() => {
    fetch.mockClear()
    WebSocket.mockClear()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders dashboard title and main sections', () => {
    // Mock the fetch calls that happen on component mount
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ workers: [] })
    })

    render(<Dashboard />)

    expect(screen.getByText('Pipeline Monitoring Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Connection Status')).toBeInTheDocument()
    expect(screen.getByText('System Health')).toBeInTheDocument()
    expect(screen.getByText('Active Workers')).toBeInTheDocument()
  })

  it('shows disconnected status initially', () => {
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ workers: [] })
    })

    render(<Dashboard />)

    expect(screen.getByText('Disconnected')).toBeInTheDocument()
    expect(screen.getByText('Attempting to connect...')).toBeInTheDocument()
  })

  it('renders circuit breakers section', () => {
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ workers: [] })
    })

    render(<Dashboard />)

    expect(screen.getByText('Circuit Breakers')).toBeInTheDocument()
  })

  it('renders recent errors section', () => {
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ workers: [] })
    })

    render(<Dashboard />)

    expect(screen.getByText('Recent Errors')).toBeInTheDocument()
    expect(screen.getByText('No recent errors')).toBeInTheDocument()
  })

  it('renders live extraction log section', () => {
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ workers: [] })
    })

    render(<Dashboard />)

    expect(screen.getByText('Live Extraction Log')).toBeInTheDocument()
  })
})
