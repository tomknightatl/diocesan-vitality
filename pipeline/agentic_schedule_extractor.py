#!/usr/bin/env python3
"""
Agentic Schedule Extractor using LangGraph

This module implements an agentic approach to parish schedule extraction
using LangGraph for orchestration and multiple specialized agents for
discovery, extraction, reasoning, and validation.

Phase 1: Proof of Concept implementation
"""

from typing import TypedDict, Optional, List, Dict
from datetime import datetime
import json
import logging

# Setup logging
logger = logging.getLogger(__name__)


class ScheduleExtractionState(TypedDict):
    """State passed between agents in the workflow"""

    parish_id: int
    parish_url: str
    schedule_type: str  # "reconciliation" or "adoration"
    knowledge_graph: Dict[str, any]
    budget_remaining: int  # Max iterations (default: 15)
    current_iteration: int
    schedule_found: bool
    final_schedule: Optional[Dict[str, any]]
    sources_checked: List[str]
    strategies_tried: List[str]
    extraction_attempts: List[str]


def create_workflow():
    """
    Create and configure the LangGraph workflow

    Returns:
        Compiled LangGraph workflow ready for execution
    """
    try:
        from langgraph.graph import StateGraph, END

        workflow = StateGraph(ScheduleExtractionState)

        # Import agents (will be implemented in subsequent steps)
        from core.agents.discovery_agent import DiscoveryAgent
        from core.agents.extraction_agent import ExtractionAgent
        from core.agents.validation_agent import ValidationAgent

        # Add nodes (agents)
        workflow.add_node("discover", DiscoveryAgent().discover_sources)
        workflow.add_node("extract", ExtractionAgent().extract_schedule)
        workflow.add_node("validate", ValidationAgent().validate_schedule)

        # Define conditional transitions
        def should_continue(state: ScheduleExtractionState) -> str:
            """Determine next action based on current state"""
            if state["schedule_found"]:
                return "validate"
            elif state["budget_remaining"] <= 0:
                return "end"
            elif len(state["sources_checked"]) == 0:
                return "discover"
            elif any(
                "reconciliation" in s.lower() or "confession" in s.lower()
                for s in state["sources_checked"]
            ):
                return "extract"
            else:
                return "end"  # No reasoning agent in Phase 1

        # Add edges
        workflow.add_conditional_edges(
            "discover", lambda state: "extract" if state["sources_checked"] else "end"
        )
        workflow.add_conditional_edges("extract", should_continue)
        workflow.add_edge("validate", END)

        # Set entry point
        workflow.set_entry_point("discover")

        return workflow.compile()

    except ImportError as e:
        logger.error(f"LangGraph not installed: {e}")
        logger.info("Installing LangGraph...")
        import subprocess

        subprocess.run(["pip", "install", "langgraph"], check=True)
        return create_workflow()
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}")
        raise


def scrape_parish_data_agentic(
    url: str, parish_id: int, supabase=None, max_iterations: int = 15
) -> dict:
    """
    Agentic replacement for existing scrape_parish_data function

    Args:
        url: Parish website URL
        parish_id: Parish database ID
        supabase: Supabase client (optional for Phase 1)
        max_iterations: Maximum workflow iterations

    Returns:
        Dictionary with schedule extraction results
    """
    logger.info(f"🤖 Starting agentic extraction for parish {parish_id}: {url}")

    # Initialize workflow
    workflow = create_workflow()

    # Set initial state
    initial_state = {
        "parish_id": parish_id,
        "parish_url": url,
        "schedule_type": "reconciliation",  # Phase 1 focus
        "knowledge_graph": {},
        "budget_remaining": max_iterations,
        "current_iteration": 0,
        "schedule_found": False,
        "final_schedule": None,
        "sources_checked": [],
        "strategies_tried": [],
        "extraction_attempts": [],
    }

    # Execute workflow
    try:
        final_state = workflow.invoke(initial_state)

        logger.info(f"🤖 Completed agentic extraction for parish {parish_id}")
        logger.info(f"🤖 Success: {final_state['schedule_found']}")

        # Format result for existing database
        if final_state["schedule_found"]:
            schedule = final_state["final_schedule"]
            return {
                "url": url,
                "offers_reconciliation": True,
                "reconciliation_info": schedule.get(
                    "schedule_details", "Schedule found"
                ),
                "reconciliation_page": schedule.get("source_url", url),
                "reconciliation_method": schedule.get("method", "agentic_ai"),
                "reconciliation_confidence": schedule.get("confidence", 80),
                "reconciliation_fact_string": schedule.get("schedule_details"),
            }
        else:
            return {
                "url": url,
                "offers_reconciliation": False,
                "reconciliation_info": "No schedule found",
                "reconciliation_page": "",
                "reconciliation_method": "agentic_no_result",
                "reconciliation_confidence": 0,
                "reconciliation_fact_string": None,
            }

    except Exception as e:
        logger.error(f"🤖 Agentic extraction failed for {url}: {e}")
        return {
            "url": url,
            "offers_reconciliation": False,
            "reconciliation_info": f"Extraction error: {str(e)}",
            "reconciliation_page": "",
            "reconciliation_method": "agentic_error",
            "reconciliation_confidence": 0,
            "reconciliation_fact_string": None,
        }
