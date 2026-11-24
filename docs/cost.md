# Cost

What the sample costs to run in your account: a small fixed amount while it sits idle, plus a per-scan amount that is mostly model tokens. Every figure on this page is either measured on a test stack (and says when) or an estimate built from measured usage and AWS list prices (and says so).

**On this page:** [Summary](#summary) · [Per scan, direct path](#per-scan-direct-path-2026-11-03) · [By service](#by-service) · [Monthly examples](#monthly-examples) · [How the service estimates were made](#how-the-service-estimates-were-made) · [Track your own spend](#track-your-own-spend)

## Summary

| Item | Amount | Basis |
| --- | --- | --- |
| Idle stacks, per month | About $14 to $15 | Estimate; Cost Explorer agreed for the tagged stacks over 2026-10-15 to 2026-10-18. Mostly the AWS WAF web ACL ($11) and two KMS keys ($2) |
| Model tokens per model-backed scan, current default (Harness path) | $0.0979 mean, $0.0988 median, $0.1237 p90 ($0.0895 per submitted URL, because 8.7% end at the pre-check) | Measured 2026-11-24, 548 model-backed scans of 600 URLs, episodic memory on ([README](../README.md#measured-results)) |
| Model tokens per model-backed scan, direct path (the default from 2026-11-03 to 2026-11-15) | $0.090 mean | Measured 2026-11-03, 407 live URLs; the current default is in the [README](../README.md#measured-results), `cost_usd` per scan ([evaluation.md](evaluation.md#latency-flags-on-by-default-2026-11-03)) |
| Other services per URL | About $0.0117 | Measured 2026-11-24 on the current default (AgentCore, Lambda, Web Search, Gateway, Memory retrieval), plus the 2026-10-19 estimates for Guardrails, DynamoDB, S3, SQS, CloudWatch, API Gateway and ECR ([By service](#by-service)) |
| Dead link (HTTP 404, Site down) | No model call | By default the pre-check runs before any model, so only the pre-check navigation is billed. On the direct path (`-c directOrchestration=true`) the specialists start with the pre-check and still bill their tokens, although the scan's `cost_usd` is `0` ([architecture.md](architecture.md#fast-paths-error-404-and-site-down)) |

## Per scan, direct path (2026-11-03)

Measured on 2026-11-03 on a test stack in `us-west-2`, 448 URLs submitted at once (224 from a public phishing feed, 224 legitimate pages), 407 live, episodic memory off, `scanConcurrency` 25:

| Configuration | Model cost per scan, mean | Scan time, median / p90 |
| --- | --- | --- |
| Direct path, all latency flags on (default 2026-11-03 to 2026-11-15) | **$0.090** | **18.6 s / 31.2 s** |
| Previous default (2026-11-02) | $0.134 | 37.8 s / 71.9 s |

Earlier measurements (2026-10-18 to 2026-11-02) are in [evaluation.md](evaluation.md#cost-history). Long pages cost more than short ones; `cost_usd` on each scan record has the exact figure.

## By service

Measured on 2026-11-24 on the current default (pre-check first, AgentCore Harness, the dispatcher as a Lambda target, web search on Gateway `phish-tools`) during the 600-URL run in [evaluation.md](evaluation.md#current-default-2026-11-24): 548 model-backed scans, 52 ended at the pre-check, nothing else running on the test stack. Token, AgentCore, Web Search, Gateway, Memory retrieval and Lambda rows are measured usage at list prices; the rest are the 2026-10-19 estimates, not re-measured. Per 100 submitted URLs in this mix.

| Service                                                | What drives cost                                                              | Idle per month                     | Per 100 URLs     | Basis                           |
| ------------------------------------------------------ | ----------------------------------------------------------------------------- | ---------------------------------- | ---------------- | ------------------------------- |
| Amazon Bedrock, Claude Opus 5.5                        | Orchestrator tokens: verdict turn and report turn, with prompt caching       | $0                                 | $4.93            | Measured                        |
| Amazon Bedrock, Claude Sonnet 5.5                      | Specialist tokens, 3 per model-backed scan, with prompt caching              | $0                                 | $4.01            | Measured                        |
| AgentCore Runtime, Harness (orchestrator)              | Active vCPU and memory during the two turns                                   | $0                                 | $0.23            | Measured usage                  |
| AgentCore Runtime, tools MCP server                    | The pre-check and every tool call (capture, page code, RDAP)                  | $0                                 | $0.29            | Measured usage                  |
| AgentCore Runtime, 3 specialists                       | `url_analyst` $0.071, `brand_visual` $0.075, `code_analyst` $0.075            | $0                                 | $0.22            | Measured usage                  |
| AgentCore Browser                                      | 2.75 sessions per URL: the pre-check and two page captures                    | $0                                 | $0.05            | Measured usage                  |
| AgentCore Web Search                                   | 0.13 queries per URL, $7 per 1,000                                            | $0                                 | $0.09            | Measured count                  |
| AgentCore Gateway                                      | About 15 invocations per URL across both Gateways, every MCP method           | Under $0.01                        | $0.01            | Measured count                  |
| AgentCore Memory                                       | About 1 retrieval and 1 record per URL; records kept (see Monthly examples)   | $0.00075 per stored record         | $0.05            | Measured count                  |
| AWS Lambda, worker                                     | Waits on the Harness: billed median 69.6 s at 512 MB                          | About $0.03                        | $0.05            | Measured duration               |
| AWS Lambda, dispatcher                                 | Waits on the specialists: billed median 13.8 s, p90 21.8 s at 512 MB          | $0                                 | $0.009           | Measured duration               |
| AWS Lambda, API, stats and sweeper                     | Requests and the 5-minute sweep                                               | Included above                     | Under $0.001     | Measured duration               |
| Amazon Bedrock Guardrails                              | URL input check, report output check                                          | $0                                 | $0.08            | Estimate                        |
| Amazon DynamoDB                                        | On-demand reads and writes; the sweeper queries a status index                | Under $0.01                        | $0.01 to $0.02   | Estimate from measured units    |
| Amazon S3                                              | 5 objects per scan, about 100 KB                                              | Under $0.10                        | Under $0.01      | Estimate                        |
| Amazon SQS                                             | Messages and idle Lambda polling                                              | About $0.36                        | Under $0.01      | Estimate from measured requests |
| API Gateway, CloudFront, Cognito                       | Requests; Cognito is free under 10,000 monthly active users                   | $0                                 | About $0.02      | Estimate                        |
| AWS WAF                                                | 1 web ACL and 6 rules                                                         | $11.00                             | Under $0.01      | Estimate, Cost Explorer agrees  |
| AWS KMS                                                | 2 customer managed keys                                                       | $2.00                              | Under $0.01      | Estimate, Cost Explorer agrees  |
| Amazon CloudWatch                                      | 10 alarms, logs, custom metrics                                               | $1.00 (up to $7 with hourly scans) | $0.02 to $0.05   | Estimate from measured bytes    |
| Amazon ECR and data transfer                           | Agent container images, regional transfer                                     | $0.10 to $1.00                     | About $0.02      | Estimate                        |
| **Total**                                              |                                                                               | **About $14 to $15**               | **About $10.12** | Tokens $8.95, the rest $1.17    |
| AWS Agent Registry (only with `-c agentRegistry=true`) | 5 records, 1 search per URL, 1 more Gateway call                              | $0 (free tier)                     | About $0.0005    | Estimate                        |

**The dispatcher Lambda costs about $0.00009 per URL** (under a cent per 100 URLs). Moving it from an AgentCore Runtime to a Lambda target was about simplicity and having no idle runtime, not about cost: the old dispatcher Runtime was measured at up to about $0.05 per 100 URLs, and the whole AgentCore Runtime line is about $0.74 per 100 URLs either way. It uses at most 117 MB of its 512 MB.

## Monthly examples

Computed from the 2026-11-24 measurement: $0.0895 of model tokens per submitted URL (the $0.0979 model-backed mean, with 8.7% of URLs ending at the pre-check), $0.0117 of other services per URL, the idle estimate, and AgentCore Memory records kept for 90 days (three months of scans stored in steady state, $0.00075 per record per month).

| URLs per month | Model tokens | Other per-URL services | Idle stacks | Stored memory records | Total |
| --- | --- | --- | --- | --- | --- |
| 1,000 | $90 | $12 | $14 to $21 | $2.25 | **About $130 to $140** |
| 10,000 | $895 | $117 | $21 | $22.50 | **About $1,060** |
| 100,000 | $8,950 | $1,170 | $21 | $225 | **About $10,370** |
| 1,000,000 | $89,460 | $11,700 | $21 | $2,250 | **About $103,400 ($0.101 per URL)** |

The 1,000,000-URL month by service, from the same measurement:

| Service | Per URL | Per month | Basis |
| --- | --- | --- | --- |
| Bedrock, Claude Opus 5.5 (verdict and report turns) | $0.04933 | $49,333 | Measured tokens |
| Bedrock, Claude Sonnet 5.5 (3 specialists) | $0.04013 | $40,127 | Measured tokens |
| AgentCore Runtime, Harness | $0.00228 | $2,279 | Measured usage |
| AgentCore Runtime, tools MCP server | $0.00291 | $2,914 | Measured usage |
| AgentCore Runtime, 3 specialists | $0.00220 | $2,203 | Measured usage |
| AgentCore Browser | $0.00049 | $490 | Measured usage |
| AgentCore Web Search | $0.00091 | $910 | Measured count |
| AgentCore Gateway | $0.00008 | $75 | Measured count |
| AgentCore Memory, retrieval | $0.00046 | $459 | Measured count |
| AgentCore Memory, 3 million records stored (90 days) | | $2,250 | $0.00075 per record per month |
| AWS Lambda (worker, dispatcher, API, aggregator) | $0.00055 | $554 | Measured duration |
| Bedrock Guardrails | $0.00080 | $800 | Estimate |
| CloudWatch logs and spans | $0.00035 | $350 | Estimate |
| API Gateway, CloudFront | $0.00020 | $200 | Estimate |
| ECR and data transfer | $0.00020 | $200 | Estimate |
| DynamoDB | $0.00015 | $150 | Estimate |
| S3 requests and 90 days of storage | $0.00010 | $107 | Estimate, $0.023 per GB-month |
| SQS | $0.00001 | $10 | Estimate |
| Idle stacks (WAF, KMS, alarms, custom metrics) | | $21 | Idle estimate, upper end |
| **Total** | **$0.1012** | **About $103,400** | |

Model tokens are 86% of it (about $89,460); AgentCore Runtime is about $7,400 and Memory storage $2,250.

Assumptions and limits:

- `us-west-2` application and `us-east-1` edge stack, on-demand list prices, no free tier, no Savings Plans.
- Token prices from `backend/phish_backend/common/pricing.json` (AWS Price List API, checked 2026-11-24, no change since 2026-10-21): the `us.` Opus 5.5 profile at $4.40 input and $22.00 output per million tokens, the `global.` Sonnet 5.5 profile at $2.00 and $10.00, cache reads at 0.05 times and 5-minute cache writes at 1.25 times the input price.
- The URL mix of the 2026-11-24 run: 8.7% of URLs end at the pre-check with no model cost. If every URL is live and model-backed, the 1,000,000-URL month is about $111,900; each 1% of dead links moves it by about $1,000. Long pages with large scripts cost more.
- Episodic memory on (the default) with records kept 90 days, so 1,000,000 URLs a month keeps about 3 million records. The $0.0979 token mean includes the orchestrator reading up to three short past-scan summaries.
- AgentCore Runtime on the consumption rates this account is billed on, $0.0895 per vCPU-hour and $0.00945 per GB-hour. The AWS Price List also carries second-tier (`v2`) consumption rates, $0.1276 per vCPU-hour and $0.0169 per GB-hour; at those rates the Runtime line would be about $1.20 instead of $0.74 per 100 URLs, about $12,000 instead of $7,400 a month at 1,000,000 URLs. Check which rates your account is billed on in Cost Explorer.
- Capacity is not priced. 1,000,000 URLs a month is about 23 a minute on average, which at a 60 s scan is about 23 scans in flight; the default `scanConcurrency` is 25, so raise it and the Bedrock and AgentCore quotas for peaks.
- The idle range tops out at $21 when CloudWatch custom metrics are published every hour.

### How the service estimates were made

Token rows come from the scan records of the 2026-11-24 run (recorded `cost_usd` matched a recomputation from stored usage on 548 of 548 model-backed scans). Other usage comes from the run's window (2026-11-24 00:13 to 01:05 UTC, test stack, nothing else running): CloudWatch `AWS/Bedrock-AgentCore` vCPU-hour and GB-hour metrics summed per resource (the per-resource sums equal the service total), Gateway and Browser invocations, and Lambda billed durations from the function logs, multiplied by AWS list prices from the AWS Price List API, checked 2026-11-24.

| Service                                                | Observed for 600 URLs                                                                                      | Unit price (us-west-2)                                                                                        | Per 100 URLs                                 |
| ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| AgentCore Runtime, Harness                             | 7.739 vCPU-hours, 71.40 GB-hours; 1,099 invocations                                                        | $0.0895 per vCPU-hour, $0.00945 per GB-hour                                                                   | $0.228                                       |
| AgentCore Runtime, tools MCP server                    | 8.153 vCPU-hours, 107.82 GB-hours; 5,544 invocations                                                       | Same                                                                                                          | $0.291                                       |
| AgentCore Runtime, `url_analyst`                       | 1.995 vCPU-hours, 26.05 GB-hours                                                                           | Same                                                                                                          | $0.071                                       |
| AgentCore Runtime, `brand_visual`                      | 2.009 vCPU-hours, 28.34 GB-hours                                                                           | Same                                                                                                          | $0.075                                       |
| AgentCore Runtime, `code_analyst`                      | 2.015 vCPU-hours, 28.47 GB-hours                                                                           | Same                                                                                                          | $0.075                                       |
| AgentCore Runtime, total (4 Runtimes plus the Harness) | 21.91 vCPU-hours, 262.08 GB-hours                                                                          | Same                                                                                                          | $0.74                                        |
| AgentCore Browser                                      | 2.118 vCPU-hours, 11.08 GB-hours; 1,648 sessions                                                           | Same                                                                                                          | $0.049                                       |
| AgentCore Web Search                                   | 78 queries (78 scans searched once, none twice)                                                            | $7 per 1,000                                                                                                  | $0.091                                       |
| AgentCore Gateway                                      | 9,014 invocations across both Gateways (2,276 of them tool calls)                                          | $0.005 per 1,000                                                                                              | $0.008                                       |
| AgentCore Memory                                       | 551 retrievals, 548 records written                                                                        | $0.50 per 1,000 retrievals; $0.75 per 1,000 records per month                                                 | $0.046 (retrieval)                           |
| Lambda, dispatcher                                     | 548 invocations, billed median 13.8 s, p90 21.8 s, mean 15.1 s, 512 MB (117 MB used); 4,136 GB-seconds     | $0.0000133334 per GB-second (Arm), $0.20 per million requests                                                 | $0.009                                       |
| Lambda, worker                                         | 670 invocations, billed median 69.6 s, p90 88.4 s, 512 MB; 20,565 GB-seconds                               | Same                                                                                                          | $0.046                                       |
| Lambda, API and stats aggregator                       | 1,319 and 2,027 invocations, 150 GB-seconds                                                                | Same                                                                                                          | Under $0.001                                 |
| Bedrock Guardrails                                     | 1 text unit in, about 4 out (2026-10-19)                                                                   | $0.15 per 1,000 text units (content and topic), $0.10 (sensitive information)                                 | $0.08                                        |
| DynamoDB                                               | 2,745 read and 3,848 write request units per 50 URLs, plus index writes (2026-10-19)                       | $0.125 per million reads, $0.625 per million writes                                                           | $0.01 to $0.02                               |
| SQS                                                    | About 230 requests per 50 URLs (2026-10-19)                                                                | $0.40 per million                                                                                             | Under $0.01                                  |
| S3                                                     | 5 PUTs and about 100 KB per scan (2026-10-19)                                                              | $0.005 per 1,000 PUTs, $0.023 per GB-month                                                                    | Under $0.01                                  |
| CloudWatch                                             | 12.7 MB of logs and spans per 50 URLs (2026-10-19)                                                         | $0.50 per GB ingested                                                                                         | $0.02 to $0.05                               |

Idle items: AWS WAF $5 per web ACL and $1 per rule per month; AWS KMS $1 per key per month; CloudWatch $0.10 per alarm per month and up to $6 for 20 custom metrics when scans run every hour; SQS long polling by the Lambda event source mappings (about 30,000 empty receives per day); the sweeper Lambda every 5 minutes. The status index adds about 6 write request units per scan (about $0.38 per 100,000 URLs); before it, the sweeper read the whole table, about $0.0015 per stored scan per month (about $450 per month at 100,000 URLs per month). Cost Explorer for the tagged stacks over 2026-10-15 to 2026-10-18 matched the idle figures within the ranges above.

The token cost of each scan is in the scan record (`cost_usd`). A model with no price in `pricing.json` is listed in `unpriced_models` and shown as unknown cost, not as free. Costs of earlier designs are in [evaluation.md](evaluation.md#cost-history).


## Track your own spend

> **Tip:** For your real spend, open the Insights page: it shows token cost per URL, per batch and per model. For everything else, filter Cost Explorer on the `Project` and `Owner` tags.
