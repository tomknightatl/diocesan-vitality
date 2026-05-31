#!/usr/bin/env python3
"""
Simple validation script for Phase 1 Model Upgrades.

This script validates the configuration changes without requiring
the google.generativeai module.
"""

import sys
import yaml
from pathlib import Path

def validate_config():
    """Validate the updated configuration file."""
    print("=" * 60)
    print("Phase 1 Model Upgrades - Configuration Validation")
    print("=" * 60)

    config_path = Path("config/ai_config.yaml")
    backup_path = Path("config/ai_config.yaml.backup")

    # Check backup exists
    if not backup_path.exists():
        print(f"\n✗ Backup file not found: {backup_path}")
        return False
    else:
        print(f"\n✓ Backup file exists: {backup_path}")

    # Load and validate configuration
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        print("\n✓ Configuration file loaded successfully")

        # Validate model assignments
        print("\n" + "-" * 60)
        print("Component Model Assignments:")
        print("-" * 60)

        expected_models = {
            "content_analyzer": "gemini-2.5-pro",
            "schedule_extractor": "gemini-3.1-flash-preview",
            "fallback_extractor": "gemini-2.5-pro",
            "url_filter": "gemini-2.5-flash-lite",
            "parish_prioritizer": "gemini-3.1-flash-preview",
        }

        component_models = config.get("models", {}).get("components", {})
        all_correct = True

        for component, expected_model in expected_models.items():
            actual_model = component_models.get(component)
            if actual_model == expected_model:
                print(f"  ✓ {component}: {actual_model}")
            else:
                print(f"  ✗ {component}: Expected {expected_model}, got {actual_model}")
                all_correct = False

        # Validate component parameters
        print("\n" + "-" * 60)
        print("Component-Specific Parameters:")
        print("-" * 60)

        component_params = config.get("component_parameters", {})

        # Check content_analyzer parameters
        ca_params = component_params.get("content_analyzer", {})
        if ca_params.get("thinking_enabled") and ca_params.get("thinking_budget") == 8192:
            print(f"  ✓ content_analyzer: thinking_enabled=True, thinking_budget=8192")
        else:
            print(f"  ✗ content_analyzer: Missing or incorrect thinking parameters")
            all_correct = False

        # Check schedule_extractor temperature
        se_params = component_params.get("schedule_extractor", {})
        if se_params.get("temperature") == 0.3:
            print(f"  ✓ schedule_extractor: temperature=0.3")
        else:
            print(f"  ✗ schedule_extractor: Expected temperature=0.3, got {se_params.get('temperature')}")
            all_correct = False

        # Check fallback_extractor parameters
        fe_params = component_params.get("fallback_extractor", {})
        if fe_params.get("thinking_enabled") and fe_params.get("thinking_budget") == 16384:
            print(f"  ✓ fallback_extractor: thinking_enabled=True, thinking_budget=16384")
        else:
            print(f"  ✗ fallback_extractor: Missing or incorrect thinking parameters")
            all_correct = False

        # Check url_filter temperature
        uf_params = component_params.get("url_filter", {})
        if uf_params.get("temperature") == 0.1:
            print(f"  ✓ url_filter: temperature=0.1")
        else:
            print(f"  ✗ url_filter: Expected temperature=0.1, got {uf_params.get('temperature')}")
            all_correct = False

        # Check parish_prioritizer temperature
        pp_params = component_params.get("parish_prioritizer", {})
        if pp_params.get("temperature") == 0.5:
            print(f"  ✓ parish_prioritizer: temperature=0.5")
        else:
            print(f"  ✗ parish_prioritizer: Expected temperature=0.5, got {pp_params.get('temperature')}")
            all_correct = False

        # Validate cost optimization settings
        print("\n" + "-" * 60)
        print("Cost Optimization Settings:")
        print("-" * 60)

        cost_opt = config.get("cost_optimization", {})
        expected_cost_opt = {
            "enabled": True,
            "budget_limit_usd": 100.0,
            "daily_quota_tokens": 1000000,
            "prefer_cheaper_models": True,
            "enable_smart_routing": True,
        }

        for key, expected_value in expected_cost_opt.items():
            actual_value = cost_opt.get(key)
            if actual_value == expected_value:
                print(f"  ✓ {key}: {actual_value}")
            else:
                print(f"  ✗ {key}: Expected {expected_value}, got {actual_value}")
                all_correct = False

        # Final summary
        print("\n" + "=" * 60)
        if all_correct:
            print("✓ All configuration changes validated successfully!")
            print("=" * 60)
            return 0
        else:
            print("✗ Some configuration validations failed.")
            print("=" * 60)
            return 1

    except Exception as e:
        print(f"\n✗ Configuration validation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


def show_diff():
    """Show differences between original and new configuration."""
    print("\n" + "=" * 60)
    print("Configuration Changes Summary")
    print("=" * 60)

    try:
        with open("config/ai_config.yaml.backup", 'r') as f:
            original = yaml.safe_load(f)

        with open("config/ai_config.yaml", 'r') as f:
            updated = yaml.safe_load(f)

        print("\nModel Upgrades:")
        print("-" * 60)

        original_models = original.get("models", {}).get("components", {})
        updated_models = updated.get("models", {}).get("components", {})

        for component in original_models:
            old_model = original_models.get(component)
            new_model = updated_models.get(component)
            if old_model != new_model:
                print(f"  {component}:")
                print(f"    - {old_model}")
                print(f"    + {new_model}")

        print("\nNew Features:")
        print("-" * 60)

        if "component_parameters" in updated and "component_parameters" not in original:
            print("  + Component-specific parameters section added")

        if "cost_optimization" in updated and "cost_optimization" not in original:
            print("  + Cost optimization section added")

    except Exception as e:
        print(f"Could not show diff: {e}")


if __name__ == "__main__":
    result = validate_config()
    show_diff()
    sys.exit(result)