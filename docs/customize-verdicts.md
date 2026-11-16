# Tune confidence, risk and actions

Every scan returns a `verdict`, a `risk_score` from 0 to 100, a `confidence` (`low`, `medium` or `high`), an `action` (`block`, `warn` or `allow`) and `page_observed`. You can match these to your own risk appetite at four layers. Start with the first: it needs no redeploy and changes nothing for other users of the stack.

> [!IMPORTANT]
> Verdicts are advisory. Whatever you tune, a person makes the final call on a held link, and the human-review disclaimer stays on every result ([Responsible AI](responsible-ai.md)). Do not remove the guardrails or the disclaimer to change outcomes.

**On this page:** [1. Your gate](#1-your-gate-no-redeploy) · [2. Orchestrator rules](#2-orchestrator-rules-redeploy) · [3. Specialist prompts](#3-specialist-prompts-and-confidence-redeploy) · [4. Caps in code](#4-caps-in-code-redeploy-and-tests) · [Measure every change](#measure-every-change)

## 1. Your gate (no redeploy)

Decide in your own client from the fields of `GET /scans/{id}` ([api.md](api.md#use-it-as-a-pre-publish-gate)). The gate script in [getting started](getting-started.md#test-the-api-a-pre-publish-gate) holds a link when the scan failed, the action is `block` or `warn`, the risk is at or above `THRESHOLD` (70), or `page_observed` is `false`.

| Policy | Hold a link for review when | Trade-off |
| --- | --- | --- |
| Strict (the example gate) | The scan failed, `action` is `block` or `warn`, `risk_score` is 70 or more, or `page_observed` is `false` | Catches the most; people review every Suspicious and Unknown verdict and every hidden page |
| Balanced | The scan failed, `action` is `block`, or `risk_score` is 70 or more | Fewer reviews; Suspicious pages below risk 70 are published, including pages hidden behind a provider warning (risk at most 69) |
| Lenient | The scan failed or `action` is `block` | Fewest reviews; only confident phishing is held |

Each is a one-line change to the `review` expression in the gate script. Balanced:

```python
review = scan["status"] == "FAILED" or verdict.get("action") == "block" or verdict.get("risk_score", 0) >= THRESHOLD
```

Lenient:

```python
review = scan["status"] == "FAILED" or verdict.get("action") == "block"
```

To act on confidence as well, add for example `or verdict.get("confidence") == "low"`. Keep a person in the loop for every held link.

## 2. Orchestrator rules (redeploy)

The orchestrator's verdict, risk, confidence and action rules are in [`agents/orchestrator/prompt.md`](../agents/orchestrator/prompt.md) (the direct path uses [`backend/phish_backend/worker/orchestrator_direct.md`](../backend/phish_backend/worker/orchestrator_direct.md); change both if you use either path):

| Rule | Where |
| --- | --- |
| Action mapping: `block` for confident phishing, `warn` for suspicious or low-confidence phishing, `allow` only for legitimate | Around line 182 |
| Confidence caps, for example two or more failed findings mean confidence at most medium | Around line 180 |
| Error 404 and Site down: risk 10, confidence high, action allow | Around lines 169 to 177 |
| The verdict JSON shape | Around line 200 |

Edit the rule in plain English, then redeploy with the same options you deployed with (`npx aws-cdk@2.1143.0 deploy --all -c owner=<team or alias>`); the stack loads the prompt into the Harness. Keep the JSON field names and the enum values exactly as they are (`phishing`, `suspicious`, `legitimate`, `unknown`, `error_404`, `site_down`; `low`, `medium`, `high`; `block`, `warn`, `allow`): the worker parses them into the `Verdict` model in `contracts/phish_contracts/models.py` and rejects a value it does not know.

## 3. Specialist prompts and confidence (redeploy)

Each specialist scores its own `confidence` from 0 to 100 (`Finding.confidence` in `agents/phish_agents/common/finding.py`) and lists signals with a severity. Their prompts are `agents/phish_agents/url_analyst/prompt.md`, `agents/phish_agents/brand_visual/prompt.md` and `agents/phish_agents/code_analyst/prompt.md`. Change what a specialist counts as evidence or how sure it should be there, then redeploy. The orchestrator weighs these findings, so a change here moves the final verdict only indirectly; measure it.

## 4. Caps in code (redeploy and tests)

A few outcomes are fixed in code, after the model answers, so a prompt cannot override them:

| Cap | Where | Tests to update and run |
| --- | --- | --- |
| Page not observed: a provider warning hid the page, or only the www. sibling was captured, so the verdict is at most `suspicious`, risk at most 69 (`UNOBSERVED_RISK_CAP`), action `warn` | `cap_unobserved_warning` in `contracts/phish_contracts/observation.py` | `contracts/tests/test_observation.py`, `contracts/tests/test_page_state.py` |
| Untrusted certificate: `legitimate` becomes `unknown` and `allow` becomes `warn` | `cap_untrusted_certificate` in the same file | `contracts/tests/test_page_state.py` |
| Both caps applied to every stored verdict | `judge()` in `backend/phish_backend/worker/verdict.py` | `contracts/tests/test_page_state.py`, `contracts/tests/test_bot_blocked.py` |
| Unanimous fast path: all three specialists legitimate with confidence 80 or more skip the verdict call (direct path only) | `UNANIMOUS_MIN_CONFIDENCE` in `backend/phish_backend/worker/direct.py` | `backend/tests/test_direct_orchestration.py` |

Run `uv run pytest contracts/tests backend/tests` after the change, then the full suite (`uv run python scripts/prepush.py`) before you deploy. These caps exist so that an unseen page or an untrusted certificate never produces a confident `allow`; loosen them only with care.

## Measure every change

Prompts and caps are tuned together, so measure before and after on your own labelled URLs with [`eval/evaluate_agents.py`](evaluation.md#run-it). `--suspicious-as phishing` (the default) scores a Suspicious verdict as caught, which matches a gate that holds `warn`; `--suspicious-as legitimate` matches a lenient gate that holds only `block`. Compare recall, false positives, scan time and cost, and deploy a second copy with `-c appName=<name>` to compare side by side.
