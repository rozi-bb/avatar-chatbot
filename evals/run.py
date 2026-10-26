"""Run Wayan's LangSmith evaluations: uv run python -m evals.run.

Syncs each suite's dataset to LangSmith, runs the graph on every example as a
new experiment, and exits non-zero if any score is below its target. Calls
DeepSeek for real, so it costs a little money. Name suites to run only those:
uv run python -m evals.run hotel culture.
"""

from __future__ import annotations

import asyncio
import sys
from collections import defaultdict
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langsmith import Client, aevaluate

from agent.graph import MODEL_NAME, Context, graph
from evals import bahasa, culture, goodbye, hotel, injection, safety
from evals import format as format_suite

SUITES = {
    "format": format_suite,
    "hotel": hotel,
    "culture": culture,
    "safety": safety,
    "injection": injection,
    "goodbye": goodbye,
    "bahasa": bahasa,
}


def sync_dataset(client: Client, suite: Any) -> None:
    """Make the suite's LangSmith dataset hold exactly the suite's examples."""
    if not client.has_dataset(dataset_name=suite.DATASET):
        client.create_dataset(dataset_name=suite.DATASET, description=suite.DESCRIPTION)
    current = list(client.list_examples(dataset_name=suite.DATASET))
    wanted = [(e["inputs"], e["outputs"]) for e in suite.EXAMPLES]
    if sorted(map(repr, wanted)) == sorted(
        repr((e.inputs, e.outputs)) for e in current
    ):
        return
    if current:
        client.delete_examples(example_ids=[e.id for e in current])
    dataset = client.read_dataset(dataset_name=suite.DATASET)
    client.create_examples(dataset_id=dataset.id, examples=suite.EXAMPLES)
    print(f"{suite.DATASET}: dataset updated ({len(suite.EXAMPLES)} examples)")


async def target(inputs: dict[str, Any]) -> dict[str, Any]:
    """Run Wayan on one example, as the kiosk would, and return what he says."""
    messages: list[AnyMessage] = [
        HumanMessage(m["content"]) if m["role"] == "user" else AIMessage(m["content"])
        for m in inputs["messages"]
    ]
    context = Context(
        channel="eval", now=inputs.get("now"), language=inputs.get("language", "en")
    )
    state = await graph.ainvoke({"messages": messages}, context=context)
    return {"reply": state["messages"][-1].text, "end_session": state["end_session"]}


async def run_suite(suite: Any) -> bool:
    """Run one suite and print its scores; return True if every target is met."""
    results = await aevaluate(
        target,
        data=suite.DATASET,
        evaluators=suite.EVALUATORS,
        experiment_prefix=suite.DATASET,
        metadata={"model": MODEL_NAME},
        max_concurrency=4,
    )
    scores: dict[str, list[bool]] = defaultdict(list)
    async for row in results:
        reply = row["run"].outputs or {}
        for result in row["evaluation_results"]["results"]:
            if result.score is None:  # the evaluator doesn't apply to this example
                continue
            scores[result.key].append(bool(result.score))
            if not result.score:
                print(f"  FAIL {result.key}: {result.comment} | {reply.get('reply')!r}")
    passed = True
    for key, target_share in suite.TARGETS.items():
        share = sum(scores[key]) / len(scores[key])
        ok = share >= target_share
        passed &= ok
        print(
            f"{suite.DATASET} {key}: {share:.0%} (target {target_share:.0%}) {'PASS' if ok else 'FAIL'}"
        )
    print(f"experiment: {results.experiment_name}")
    return passed


async def main(names: list[str]) -> int:
    """Sync datasets, run the named suites (all by default), return the exit code."""
    load_dotenv(".env")
    client = Client()
    ok = True
    for suite in [SUITES[name] for name in names or SUITES]:
        sync_dataset(client, suite)
        ok &= await run_suite(suite)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
