"""Automated AI evaluation suite running golden emails against the decision pipeline."""

import asyncio
import logging
import sys
from typing import Any

from app.ai.decide import decide
from app.ai.schemas import Decision
from app.config import settings
from evals.golden_emails import ALL_EVAL_EMAILS, REFERENCE_GOLDEN_EMAILS

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("evals")


async def run_single_eval(case: dict[str, Any]) -> dict[str, Any]:
    """Run one golden case through the decide function and evaluate accuracy."""
    name = case["name"]
    expected_section = case["section"]
    expected_action = case["action"]
    email_text = case["email"]

    decision: Decision = await decide(email_text)

    # For safety/escalation rules, section='escalation-rules' or the specific product category is acceptable if action matches
    section_match = (decision.section == expected_section) or (
        expected_action == "escalate"
        and decision.action == "escalate"
        and decision.section in (expected_section, "escalation-rules")
    )
    action_match = decision.action == expected_action
    passed = section_match and action_match

    return {
        "name": name,
        "passed": passed,
        "section_match": section_match,
        "action_match": action_match,
        "expected_section": expected_section,
        "actual_section": decision.section,
        "expected_action": expected_action,
        "actual_action": decision.action,
        "proposed_action": decision.proposed_action,
        "reason": decision.reason,
    }


async def main():
    logger.info("==================================================================")
    logger.info(
        "Running ResolveHelm Golden Evaluations (%d test cases)...",
        len(ALL_EVAL_EMAILS),
    )
    logger.info(
        "App Env: %s | Classifier: %s | Agent: %s",
        settings.APP_ENV,
        settings.CLASSIFIER_MODEL,
        settings.AGENT_MODEL,
    )
    logger.info("==================================================================")

    results = []
    for case in ALL_EVAL_EMAILS:
        res = await run_single_eval(case)
        results.append(res)
        status_sym = "PASS" if res["passed"] else "FAIL"
        logger.info(
            "[%s] %-28s | Section: %-15s (exp: %-15s) | Action: %-8s (exp: %-8s)",
            status_sym,
            res["name"],
            res["actual_section"],
            res["expected_section"],
            res["actual_action"],
            res["expected_action"],
        )

    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    action_matches = sum(1 for r in results if r["action_match"])
    accuracy = (passed_count / total_count) * 100.0

    # Specifically check the 18 reference golden emails
    ref_names = {c["name"] for c in REFERENCE_GOLDEN_EMAILS}
    ref_results = [r for r in results if r["name"] in ref_names]
    ref_passed = sum(1 for r in ref_results if r["passed"])

    logger.info("------------------------------------------------------------------")
    logger.info("EVALUATION SUMMARY:")
    logger.info(
        "Reference Golden Cases: %d/%d passed (%.1f%%)",
        ref_passed,
        len(REFERENCE_GOLDEN_EMAILS),
        (ref_passed / len(REFERENCE_GOLDEN_EMAILS)) * 100,
    )
    logger.info(
        "Total Evaluated Cases:  %d/%d passed (%.1f%%)",
        passed_count,
        total_count,
        accuracy,
    )
    logger.info(
        "Action Accuracy:        %d/%d (%.1f%%)",
        action_matches,
        total_count,
        (action_matches / total_count) * 100,
    )
    logger.info("------------------------------------------------------------------")

    if ref_passed < len(REFERENCE_GOLDEN_EMAILS):
        logger.error("Release gate failed: Not all reference golden cases passed.")
        sys.exit(1)

    logger.info("All reference release gates PASSED.")
    return 0


if __name__ == "__main__":
    asyncio.run(main())
