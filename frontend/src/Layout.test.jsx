import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Layout from './Layout'

// Wrapper component for Router context
const LayoutWrapper = ({ children }) => (
  <BrowserRouter>
    {children}
  </BrowserRouter>
)

describe('Layout Component', () => {
  it('renders navigation bar', () => {
    render(
      <LayoutWrapper>
        <Layout />
      </LayoutWrapper>
    )

    // Check for navigation elements
    expect(screen.getByRole('navigation')).toBeInTheDocument()
  })

  it('renders navigation links', () => {
    render(
      <LayoutWrapper>
        <Layout />
      </LayoutWrapper>
    )

    // Check for specific navigation links
    expect(screen.getByText('Dioceses')).toBeInTheDocument()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Reports')).toBeInTheDocument()
  })

  it('has correct link destinations', () => {
    render(
      <LayoutWrapper>
        <Layout />
      </LayoutWrapper>
    )

    // Check that links have correct href attributes
    const diocesesLink = screen.getByText('Dioceses').closest('a')
    const dashboardLink = screen.getByText('Dashboard').closest('a')
    const reportsLink = screen.getByText('Reports').closest('a')

    expect(diocesesLink).toHaveAttribute('href', '/')
    expect(dashboardLink).toHaveAttribute('href', '/dashboard')
    expect(reportsLink).toHaveAttribute('href', '/reports')
  })
})
