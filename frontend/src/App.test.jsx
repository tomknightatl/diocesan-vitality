import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import App from './App'

// Mock fetch globally
global.fetch = vi.fn()

// Wrapper component for Router context
const AppWrapper = ({ children }) => (
  <BrowserRouter>
    {children}
  </BrowserRouter>
)

describe('App Component', () => {
  beforeEach(() => {
    fetch.mockClear()
  })

  it('renders loading spinner initially', () => {
    // Mock fetch to never resolve so we stay in loading state
    fetch.mockImplementation(() => new Promise(() => {}))

    render(
      <AppWrapper>
        <App />
      </AppWrapper>
    )

    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('displays dioceses table when data loads successfully', async () => {
    const mockDioceses = {
      data: [
        {
          id: 1,
          Name: 'Archdiocese of New York',
          Address: '1011 First Avenue, New York, NY 10022',
          Website: 'https://archny.org',
          parish_directory_url: 'https://archny.org/parishes',
          parishes_in_db_count: 292,
          parishes_with_data_extracted_count: 180,
          is_blocked: false,
          respectful_automation_used: true,
          status_description: 'Active'
        }
      ],
      total_count: 1
    }

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockDioceses
    })

    render(
      <AppWrapper>
        <App />
      </AppWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText('Archdiocese of New York')).toBeInTheDocument()
    })

    expect(screen.getByText('Name')).toBeInTheDocument()
    expect(screen.getByText('Address')).toBeInTheDocument()
    expect(screen.getByText('Website')).toBeInTheDocument()
    expect(screen.getByText('292')).toBeInTheDocument()
  })

  it('displays error message when fetch fails', async () => {
    fetch.mockRejectedValueOnce(new Error('Network error'))

    render(
      <AppWrapper>
        <App />
      </AppWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText(/Error fetching data: Network error/)).toBeInTheDocument()
    })
  })

  it('renders pagination controls', async () => {
    const mockDioceses = {
      data: Array.from({ length: 10 }, (_, i) => ({
        id: i + 1,
        Name: `Diocese ${i + 1}`,
        Address: `Address ${i + 1}`,
        Website: `https://diocese${i + 1}.org`,
        parishes_in_db_count: 10,
        parishes_with_data_extracted_count: 5,
        is_blocked: false,
        respectful_automation_used: true
      })),
      total_count: 100 // More than 50 (default page size) to trigger pagination
    }

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockDioceses
    })

    render(
      <AppWrapper>
        <App />
      </AppWrapper>
    )

    await waitFor(() => {
      expect(screen.getByText('Diocese 1')).toBeInTheDocument()
    })

    // Check for pagination controls
    expect(screen.getByText('1')).toBeInTheDocument() // Page number
    expect(screen.getByText('2')).toBeInTheDocument() // Page number
  })

  it('renders items per page selector', () => {
    fetch.mockImplementation(() => new Promise(() => {}))

    render(
      <AppWrapper>
        <App />
      </AppWrapper>
    )

    expect(screen.getByText('Show:')).toBeInTheDocument()
    expect(screen.getByDisplayValue('50')).toBeInTheDocument() // Default page size
  })
})
