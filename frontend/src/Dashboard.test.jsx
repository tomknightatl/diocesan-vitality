import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import Dashboard from "./Dashboard";

// Mock WebSocket
global.WebSocket = vi.fn().mockImplementation(() => ({
  close: vi.fn(),
  send: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  readyState: 1, // OPEN
}));

// Mock fetch globally
global.fetch = vi.fn();

describe("Dashboard Component", () => {
  beforeEach(() => {
    fetch.mockClear();
    WebSocket.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders dashboard title and main sections", () => {
    // Mock the fetch calls that happen on component mount
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ workers: [] }),
    });

    render(<Dashboard />);

    expect(
      screen.getByText("Pipeline Monitoring Dashboard"),
    ).toBeInTheDocument();
    expect(screen.getByText("🔴 Disconnected")).toBeInTheDocument();
    expect(screen.getAllByText("System Health")).toHaveLength(2); // Appears in card title and worker row
    expect(
      screen.getByText("👥 Worker Status & Selection"),
    ).toBeInTheDocument();
  });

  it("shows disconnected status initially", () => {
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ workers: [] }),
    });

    render(<Dashboard />);

    expect(screen.getByText("🔴 Disconnected")).toBeInTheDocument();
    expect(
      screen.getByText(
        "⚠️ Dashboard disconnected from monitoring service. Attempting to reconnect...",
      ),
    ).toBeInTheDocument();
  });

  it("renders circuit breakers section", () => {
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ workers: [] }),
    });

    render(<Dashboard />);

    expect(screen.getByText("🛡️ Circuit Breaker Status")).toBeInTheDocument();
  });

  it("renders recent errors section", () => {
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ workers: [] }),
    });

    render(<Dashboard />);

    expect(screen.getByText("Alerts")).toBeInTheDocument();
    expect(screen.getAllByText("Recent Errors")).toHaveLength(2); // Appears in worker row and Alerts card
  });

  it("renders live extraction log section", () => {
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ workers: [] }),
    });

    render(<Dashboard />);

    expect(screen.getByText("📋 Live Extraction Log")).toBeInTheDocument();
  });
});
