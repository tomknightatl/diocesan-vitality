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
    # Try direct import first (avoid subprocess if possible)
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
        logger.info(
            "LangGraph is required for agentic workflow - checking installation..."
        )

        # First, try to check if LangGraph is accessible with path adjustment
        import sys
        import subprocess
        import os

        # Try adding to sys.path directly
        try:
            sys.path.insert(0, "/tmp/.local/lib/python3.11/site-packages")
            from langgraph.graph import StateGraph, END

            logger.info("✅ LangGraph imported successfully after path adjustment")

            # Create workflow after successful import
            workflow = StateGraph(ScheduleExtractionState)
            from core.agents.discovery_agent import DiscoveryAgent
            from core.agents.extraction_agent import ExtractionAgent
            from core.agents.validation_agent import ValidationAgent

            workflow.add_node("discover", DiscoveryAgent().discover_sources)
            workflow.add_node("extract", ExtractionAgent().extract_schedule)
            workflow.add_node("validate", ValidationAgent().validate_schedule)
            workflow.set_entry_point("discover")
            return workflow.compile()
        except ImportError:
            pass

        # If direct path adjustment didn't work, try subprocess installation
        try:
            env = os.environ.copy()
            env["PYTHONPATH"] = "/tmp/.local/lib/python3.11/site-packages:" + env.get(
                "PYTHONPATH", ""
            )
            subprocess.run(["pip", "install", "langgraph"], check=True, env=env)

            # Try import again after installation
            sys.path.insert(0, "/tmp/.local/lib/python3.11/site-packages")
            from langgraph.graph import StateGraph, END

            logger.info("✅ LangGraph installed and accessible")

            # Create workflow after successful import
            workflow = StateGraph(ScheduleExtractionState)
            from core.agents.discovery_agent import DiscoveryAgent
            from core.agents.extraction_agent import ExtractionAgent
            from core.agents.validation_agent import ValidationAgent

            workflow.add_node("discover", DiscoveryAgent().discover_sources)
            workflow.add_node("extract", ExtractionAgent().extract_schedule)
            workflow.add_node("validate", ValidationAgent().validate_schedule)
            workflow.set_entry_point("discover")
            return workflow.compile()

        except Exception as e2:
            logger.error(f"LangGraph installation failed: {e2}")
            logger.error("Agentic workflow cannot proceed without LangGraph")
            # Return None to allow batch processor to continue with next parish
            return None
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
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"🤖 Starting agentic extraction for parish {parish_id}: {url}")

    # Initialize workflow
    workflow = create_workflow()

    if workflow is None:
        logger.error(f"❌ Workflow creation failed for parish {parish_id}")
        return {
            "url": url,
            "offers_reconciliation": False,
            "reconciliation_info": "Workflow creation failed",
            "reconciliation_page": "",
            "reconciliation_method": "agentic_error",
            "reconciliation_confidence": 0,
            "reconciliation_fact_string": None,
        }

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


def extract_schedule_agentic_main(
    num_parishes: int = 100,
    parish_id: Optional[int] = None,
    max_pages_per_parish: int = 10,
    monitoring_client=None,
    max_iterations: int = 15,
):
    """
    Main function for agentic schedule extraction (replaces extract_schedule_main)

    Args:
        num_parishes: Number of parishes to process
        parish_id: Specific parish ID (optional)
        max_pages_per_parish: Maximum pages to check per parish
        monitoring_client: Monitoring client for logging
        max_iterations: Maximum workflow iterations per parish
    """
    import logging
    from core.db import get_supabase_client
    from core.intelligent_parish_prioritizer import IntelligentParishPrioritizer

    logger = logging.getLogger(__name__)
    supabase = get_supabase_client()

    # Use intelligent prioritization to select parishes
    prioritizer = IntelligentParishPrioritizer()
    parishes = prioritizer.prioritize_parishes(
        limit=num_parishes, specific_parish_id=parish_id, schedule_extraction=True
    )

    logger.info(f"🤖 Starting agentic schedule extraction for {len(parishes)} parishes")

    for i, parish in enumerate(parishes, 1):
        try:
            logger.info(
                f"🤖 [{i}/{len(parishes)}] Processing parish {parish['parish_id']}: {parish['parish_website']}"
            )

            # Call agentic extraction
            result = scrape_parish_data_agentic(
                url=parish["parish_website"],
                parish_id=parish["parish_id"],
                supabase=supabase,
                max_iterations=max_iterations,
            )

            logger.info(
                f"🤖 [{i}/{len(parishes)}] Completed parish {parish['parish_id']}: {result['reconciliation_info']}"
            )

            # Log to monitoring if available
            if monitoring_client:
                monitoring_client.send_log(
                    f"Agentic extraction for parish {parish['parish_id']}: {result['reconciliation_info']}",
                    "INFO",
                    worker_type="schedule",
                )

        except Exception as e:
            logger.error(
                f"🤖 [{i}/{len(parishes)}] Failed parish {parish['parish_id']}: {e}"
            )
            if monitoring_client:
                monitoring_client.report_error(
                    error_type="AgenticExtractionError",
                    message=f"Agentic extraction failed for parish {parish['parish_id']}: {str(e)}",
                )

    logger.info(
        f"✅ Completed agentic schedule extraction for {len(parishes)} parishes"
    )
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


def extract_schedule_agentic_main(
    num_parishes: int = 100,
    parish_id: Optional[int] = None,
    max_pages_per_parish: int = 10,
    monitoring_client=None,
    max_iterations: int = 15,
):
    """
    Main function for agentic schedule extraction (replaces extract_schedule_main)

    Args:
        num_parishes: Number of parishes to process
        parish_id: Specific parish ID (optional)
        max_pages_per_parish: Maximum pages to check per parish
        monitoring_client: Monitoring client for logging
        max_iterations: Maximum workflow iterations per parish
    """
    import logging
    from typing import Optional
    from core.db import get_supabase_client
    from core.intelligent_parish_prioritizer import IntelligentParishPrioritizer

    logger = logging.getLogger(__name__)
    supabase = get_supabase_client()

    # Use intelligent prioritization to select parishes
    prioritizer = IntelligentParishPrioritizer()
    parishes = prioritizer.prioritize_parishes(
        limit=num_parishes, specific_parish_id=parish_id, schedule_extraction=True
    )

    logger.info(f"🤖 Starting agentic schedule extraction for {len(parishes)} parishes")

    for i, parish in enumerate(parishes, 1):
        try:
            logger.info(
                f"🤖 [{i}/{len(parishes)}] Processing parish {parish['parish_id']}: {parish['parish_website']}"
            )

            # Call agentic extraction
            result = scrape_parish_data_agentic(
                url=parish["parish_website"],
                parish_id=parish["parish_id"],
                supabase=supabase,
                max_iterations=max_iterations,
            )

            logger.info(
                f"🤖 [{i}/{len(parishes)}] Completed parish {parish['parish_id']}: {result['reconciliation_info']}"
            )

            # Log to monitoring if available
            if monitoring_client:
                monitoring_client.send_log(
                    f"Agentic extraction for parish {parish['parish_id']}: {result['reconciliation_info']}",
                    "INFO",
                    worker_type="schedule",
                )

        except Exception as e:
            logger.error(
                f"🤖 [{i}/{len(parishes)}] Failed parish {parish['parish_id']}: {e}"
            )
            if monitoring_client:
                monitoring_client.report_error(
                    error_type="AgenticExtractionError",
                    message=f"Agentic extraction failed for parish {parish['parish_id']}: {str(e)}",
                )

    logger.info(
        f"✅ Completed agentic schedule extraction for {len(parishes)} parishes"
    )
