# Architecture

This page shows how a scan moves through the system, which component may call which, and where data lives. It describes the default deploy (`agentRegistry=false`, `webSearch=true`, `browserSigning=false`, `episodicMemory=true`). For what each agent checks, see the [agent pages](agents/).

**On this page:** [How a scan works](#how-a-scan-works) · [Direct path (opt-in)](#direct-path-opt-in) · [Questions reviewers ask](#questions-reviewers-ask) · [Agent Registry (opt-in)](#agent-registry-opt-in) · [Fast paths](#fast-paths-error-404-and-site-down) · [Capture](#capture-warnings-redirects-and-capture-gaps) · [One batch](#one-batch) · [Where data lives](#where-data-lives) · [Why this shape](#why-this-shape)

![Architecture: users and API clients reach API Gateway directly or through CloudFront and AWS WAF; the API queues each scan on Amazon SQS for the worker Lambda. The worker first pre-checks the URL directly on the tools MCP server (step 3), then invokes the orchestrator on AgentCore Harness (step 4). Each AgentCore Gateway is a box with its targets inside. Through Gateway phish-specialists the Harness calls the dispatcher Lambda target (step 5), which invokes url_analyst, brand_visual and code_analyst, three agents exposed as MCP tools, at the same time (step 6). The specialists call their tools through Gateway phish-tools on the tools MCP server (step 7), which drives AgentCore Browser and the RDAP lookup (step 8). Two dashed lines: brand_visual calls AgentCore Web Search, the other target on phish-tools, and the Harness may call one specialist directly in an optional second round. The supporting services row has no lines](architecture.png)

## How a scan works

The diagram and these steps show the default deploy ([configuration.md](configuration.md)). The numbers match the lines in the diagram. Every call returns the way it came, and every AWS call is signed with SigV4 (IAM).

| Step | From and to | What happens |
| --- | --- | --- |
| 1 | You to the API | You submit a URL in the web app (CloudFront and AWS WAF, then a web Lambda that signs with SigV4) or call the REST API with SigV4. The API Lambda runs the input guardrail on the URL and writes a `PENDING` row to DynamoDB `scans` |
| 2 | API to SQS to worker | The API puts one message on the SQS queue. The worker Lambda takes one message at a time, at most 25 at once (`scanConcurrency`) |
| 3 | Worker to tools MCP server | **Pre-check, before any model.** The worker calls `precheck_url` on the tools MCP server (no model) directly, not through a Gateway. A final HTTP 404 or a dead site ends the scan here with a fixed report, and no specialist or orchestrator runs ([Fast paths](#fast-paths-error-404-and-site-down)) |
| 4 | Worker to Harness | The worker recalls up to 3 similar past scans from AgentCore Memory and invokes the orchestrator on AgentCore Harness (Claude Opus 5.5, effort `medium`, prompt caching on). Only the worker may invoke the Harness |
| 5 | Harness through Gateway `phish-specialists` to the dispatcher | The Harness has one tool, this Gateway. Round one is one call, `dispatcher___analyze_all`, which the Gateway routes to its Lambda target, the [dispatcher](agents/dispatcher.md) (an AWS Lambda function with no model that runs only when called) |
| 6 | Dispatcher to the 3 specialists | The dispatcher invokes `url_analyst`, `brand_visual` and `code_analyst` at the same time (Claude Sonnet 5.5 each). Each saves its Finding to S3, and the dispatcher returns the three Findings in one reply |
| 7 | Specialists through Gateway `phish-tools` to the tools MCP server | The specialists call their tools through this Gateway: `whois_lookup` (`url_analyst`), `capture_page` (`brand_visual`) and `capture_page_code` (`code_analyst`). The tools MCP server (no model) is the only component that opens a browser or writes the screenshot and page capture |
| 8 | Tools MCP server to AgentCore Browser | The tools MCP server loads the page in AgentCore Browser, and runs the RDAP lookup over the internet with answers cached in the result cache |

Then the orchestrator replies with a compact verdict, and on the same Harness session it writes the report (turn 2, no tool calls). The worker stores the verdict in `scans` (`COMPLETE`, `report_status` `PENDING`) and a one-line summary in AgentCore Memory, screens the report with the output guardrail and sets `report_status` `READY` (`FAILED` if it could not be written; the verdict stands). The page-not-observed and untrusted-certificate caps apply on every path. The Harness has no managed memory, and the worker passes `actorId` = the scan id, so no state carries from one scan to the next. When the first-round Findings conflict, or one failed and the verdict depends on it, the orchestrator may call one specialist tool (`url-analyst___analyze`, `brand-visual___analyze` or `code-analyst___analyze`, never the dispatcher) once more on the same Gateway, at most once per scan (the dashed "round 2" line).

**Agents as tools, not A2A.** The three specialists are agents (each runs its own Claude Sonnet 5.5 loop on AgentCore Runtime), but they are exposed to the orchestrator as MCP tools: each is an MCP server target on Gateway `phish-specialists`, and the orchestrator calls it like any other tool and gets a Finding back. They do not use the Agent2Agent (A2A) protocol, do not talk to each other, and do not delegate back to the orchestrator.

Not numbered:

- **Web search** (the dashed line to AgentCore Web Search). When a page names a brand whose official site the model is unsure of, `brand_visual` calls AgentCore Web Search and caches the answer. In a Region that offers the Web Search connector (`us-west-2`, the default, as well as `us-east-1`, `eu-west-1` and `ap-northeast-1`) the connector is a second target on Gateway `phish-tools`. In any other Region `brand_visual` falls back to the separate Gateway `phish-web-search` in the `us-east-1` edge stack. Because IAM is per Gateway, a client-side tool allowlist keeps web search to `brand_visual` ([security.md](security.md#generative-ai-controls)).
- **Deadlines.** Each specialist has its own deadline and writes its own Finding; a specialist that fails writes nothing and becomes an error Finding when the worker reads the Findings back.

Supporting services, and who uses them:

| Service | Used by |
| --- | --- |
| DynamoDB `scans` | The API Lambda writes `PENDING`; the worker writes the verdict and report |
| S3 artifacts | The specialists and the tools MCP server write; the worker reads the Findings |
| DynamoDB result cache | RDAP answers (tools MCP server) and web search answers (`brand_visual`) |
| AgentCore Memory | The worker only |
| Bedrock Guardrails | Input check on the URL (API Lambda and CSV splitter), output check on the report (worker) |
| AgentCore Web Search | `brand_visual` only, as a target on Gateway `phish-tools` (the fallback Gateway in the edge stack in a Region without the connector) |
| AWS Agent Registry | Not deployed by default; see [Agent Registry (opt-in)](#agent-registry-opt-in) |

Left out of the diagram: Amazon Cognito sign-in, the CSV upload and split Lambda, the stats Lambda, the sweepers, AWS KMS and Amazon CloudWatch ([security.md](security.md) covers them).

## Direct path (opt-in)

`-c directOrchestration=true` takes the Harness, the dispatcher Lambda and Gateway `phish-specialists` off the scan path (they stay deployed; the dispatcher costs nothing while it is not called). The worker starts the pre-check and the three specialist Runtimes at the same time, then asks the orchestrator model for the verdict and the report with two Converse calls. When all three specialists say legitimate with confidence 80 or more, no capture reports the page unobserved, none errored and nothing above medium was raised, it stores `legitimate`, risk 5, `allow` without the verdict call (`unanimousFastPath`). It is faster, but on a 404 or a dead site the specialists have already started, so their tokens are billed and their Findings thrown away. It has no Harness trace and no second round. `-c directTools=true` (works on either path) lets `brand_visual` and `code_analyst` call their own copy of the tools MCP server directly instead of through `phish-tools`, and `-c localRdap=true` moves the RDAP lookup into `url_analyst`'s own process. Measurements are in [evaluation.md](evaluation.md#latency-flags-on-by-default-2026-11-03).

## Questions reviewers ask

- **Does the Harness call the Gateway directly?** Yes. The Gateway is the Harness's only tool, configured in the Harness. The Harness role may invoke that one Gateway and nothing else: not a Runtime, not the dispatcher Lambda, not Gateway `phish-tools` and not the fallback web search Gateway.
- **Why a dispatcher?** The model asks for all three specialists in one message, but the Harness runs the tool calls of one turn one after another, and its APIs have no parallel tool setting. Three specialist tools would cost the sum of the three; the dispatcher runs them at the same time, so round one costs about the slowest one. The orchestrator still decides, judges and runs the second round itself.
- **Why is the dispatcher a Lambda function and not a Runtime?** It has no model and no session state: it fans out three calls and waits. As a Lambda target on `phish-specialists` it keeps the same tool name, `dispatcher___analyze_all`, runs only when the Gateway calls it, and needs no container image or always-on Runtime of its own.
- **Are the specialists A2A agents?** No. They are agents exposed as MCP tools (agents as tools) on Gateway `phish-specialists`; see [How a scan works](#how-a-scan-works). Measurements are in [orchestrator.md](agents/orchestrator.md#why-a-dispatcher) and [evaluation.md](evaluation.md#latency-history).
- **Can this be simpler to maintain?** `-c webSearch=false` and `-c episodicMemory=false` drop web search and memory, and Agent Registry is already opt-in. The tools MCP server, Gateway `phish-tools`, the pre-check and the dispatcher Lambda are always deployed. The default deploy has two Gateways, `phish-specialists` and `phish-tools`; the third, `phish-web-search` in the edge stack, is deployed only in a Region without the Web Search connector.
- **Why are the tools behind a Gateway?** One place to see, authorize and swap every tool the specialists use (the tools MCP server and, in a Region that offers it, AgentCore Web Search), the same as the specialists behind `phish-specialists`. The cost is one Gateway hop per tool call; `-c directTools=true` removes it.
- **Can a specialist call another specialist's tool?** IAM is per Gateway, so IAM alone would let any specialist role call any tool on `phish-tools`, web search included. Each specialist's MCP client lists and calls only its own tools (a client-side allowlist), so only `brand_visual` sees `web_search`. The tools MCP server validates every URL and scan id itself and the orchestrator has no access to that Gateway; an interceptor Lambda per tool would close the gap on the server side. With `-c directTools=true` each capturing specialist may invoke only its own copy of the tools MCP server.

## Agent Registry (opt-in)

AWS Agent Registry (part of Amazon Bedrock AgentCore) is a discovery and governance catalog, not a router. It is **off by default**. With `-c agentRegistry=true` (offered in `us-west-2` and `us-east-1`) the stack adds:

| Added | What it does |
| --- | --- |
| A registry with five MCP records | One per tool provider (the dispatcher, the three specialists, the tools MCP server) with its endpoint and tool list, created by the stack and auto-approved |
| A `registry` target on `phish-specialists` | Lets the orchestrator search those records; the Gateway role may search that one registry only |
| A lookup step in the orchestrator prompt | One search at the start of each scan, before the dispatcher call |

The lookup is informational. AgentCore Gateway has no target type that reads a registry record, so every call still goes to a Gateway target that points straight at a Runtime (or, for the dispatcher, the Lambda function), and round one is always the dispatcher call. If the lookup fails, the orchestrator notes it and goes on. It adds one Gateway call per scan, and in earlier measurements 0.5 to 0.8 s. Because the orchestrator can call tools only on its one Gateway, a tampered record can at most change which of that Gateway's tools the model picks ([security.md](security.md#generative-ai-controls)).

## Fast paths: Error 404 and site down

`precheck_url` opens the URL once in AgentCore Browser and reads only the final HTTP status. When the browser refuses the URL, cannot reach it or times out, the tool sends one plain HTTP probe: a GET, up to 5 redirects followed by hand, every hop checked by the same URL guard as the browser, at most 64 KB read, 8 s in total, nothing parsed or executed. The worker waits at most 22 s for the answer.

- A final HTTP 404 ends the scan as `error_404` (Error 404).
- HTTP 410, a host that does not resolve, a refused or reset connection, or a redirect to a host that does not resolve ends the scan as `site_down` (Site down). The fixed report lists the addresses tried, defanged and in order, and the reason.
- Both answers are risk 10, confidence high, action allow, with no model call: by default the pre-check runs before the Harness, so no specialist or orchestrator runs and nothing is billed beyond the pre-check. On the direct path (`-c directOrchestration=true`) the three specialists start at the same time as the pre-check, so they finish on their own and their tokens are billed, although the scan record's `cost_usd` is `0` and the worker never reads their Findings. A page that answers anything else runs the full scan, even when the browser refused it.

## Capture: warnings, redirects and capture gaps

Capture is passive, with one bounded exception. The tools MCP server opens the page, waits for it to settle, and takes a screenshot and the page code. It does not solve or wait out bot checks, and does not type or submit data into the page. The exception is a provider warning: on a Cloudflare "Suspected Phishing" or "Suspected Malware" page it clicks the warning's own proceed control once, only when Cloudflare has enabled it (the Turnstile widget that gates it is never touched), and captures the real page if that gets through.

- **Block pages are named, not guessed.** Cloudflare's "Suspected Phishing" and "Suspected Misleading Website" warnings add a `high` `cloudflare_phishing_warning` signal, and its "Suspected Malware" warning a `high` `cloudflare_malware_warning`: strong third-party evidence, not proof. When the click past it is stopped (in every interstitial saved so far the proceed button was Turnstile-gated or missing), a `low` `warning_bypass_blocked` signal is added, the screenshot is the warning, and the verdict is held at `suspicious` (risk at most 69) with a "Page not observed" note and `page_observed: false` ([orchestrator.md](agents/orchestrator.md#page-not-observed)). When it gets through, the real page is captured and judged.
- **Redirect chains are evidence.** Each browser capture records how it reached the page (`redirect_chain`: HTTP 3xx hops, script and meta refresh navigations, the warning click), every hop checked by the URL guard. `url_analyst` gets the URL's HTTP redirect chain from the same guarded probe the pre-check uses, with flags for hops to another site, to free hosting or to a shortener. A redirect to a host that does not resolve stays Site down: the pre-check catches HTTP ones before any model, and the specialists report the rest as `site_unreachable`.
- **Bot checks are named too.** A bot filter such as EggyWall adds a `medium` `cloaking_bot_filter`. An interactive bot check (Cloudflare "Just a moment", a captcha) adds a `low` `bot_challenge`. With `-c browserSigning=true` the signed browser may see fewer of these checks; it is off by default because in a 2026-10-11 test it added 1 to 4 s per page load (noted in `infra/tests/test_browser_signing.py`) and no bot check turned up to show its benefit.
- **Capture gaps are not evidence.** `blocked_by_browser` (the managed browser refused the URL before sending a request), `bot_challenge`, `tls_error` and `static_html_only` lower confidence and are never phishing evidence on their own. `static_html_only` means the browser could not load the page and `code_analyst` read a bounded excerpt of its raw HTML through the guarded HTTP probe instead, never rendered or run, so `page_observed` stays `false` ([code_analyst.md](agents/code_analyst.md#raw-html-fallback)).
- **A certificate error is not a dead site.** A certificate or TLS error (`ERR_CERT_COMMON_NAME_INVALID`, `ERR_CERT_AUTHORITY_INVALID`, `ERR_CERT_DATE_INVALID` and the other `ERR_CERT_*` and `ERR_SSL_*` codes) means the host answered, so the pre-check never ends such a scan as `site_down`: it runs in full, the specialists get a `low` `tls_error` signal and judge from the URL, and the orchestrator prompt says the verdict is never `site_down` and a bad certificate alone is not phishing.
- **No live links in prose.** The worker defangs every URL and host name in the model's summary, disagreements, missed points and report before storing them, and the HTML report defangs them again (records stored earlier included). Machine fields such as the scan's `url` are left exact.
- **Capture notes.** Code, not the model, writes `capture_note` on each Finding: one plain sentence on how the capture went, for example "Cloudflare showed its own phishing warning for this site and the browser could not get past it (its proceed button stays disabled behind a Cloudflare Turnstile check, which is never solved), so the real page was not observed." The console shows it under the screenshot.
- **Code insights.** `code_analyst` adds `insights`, a structured summary of what the page's code does: the endpoints it sends data to (defanged, off-domain first), its forms and whether script submits them, the script count and size, and the external script hosts. The console shows it in "What the page's code does". Field details are in [api.md](api.md#signals-capture-notes-and-code-insights).

> [!IMPORTANT]
> If you gate publishing on the verdict, send `action` `warn` and `verdict.page_observed: false` to human review. A page hidden behind an unpassed provider warning stays below a block threshold of 70 by design.

## One batch

1. You upload a CSV (up to 200 URLs in the app, 1,000 through the API) to a presigned Amazon S3 upload, or send up to 50 URLs as JSON.
2. For a CSV, the upload triggers the `split_csv` Lambda, which parses the rows, runs the input guardrail on each URL and writes one `PENDING` scan per URL.
3. Each scan goes on the same SQS queue and follows the single-scan path. At most 25 run at once.
4. The `batches` row keeps counts by status and verdict, cost and timings as scans finish. The app polls it every 2 seconds while a batch runs.
5. When every scan is `COMPLETE` or `FAILED`, the batch is closed. A dead-letter sweeper marks any message that could not be delivered as `FAILED` with a reason. Every 5 minutes a sweep also re-queues scans stuck in `PENDING` and marks a CSV batch whose file never arrived as `FAILED` ("CSV was never uploaded"), so no scan or batch is left hanging.

## Where data lives

| Store               | What it holds                                                     | Kept for                                                   |
| ------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------- |
| DynamoDB `scans`    | One row per URL: status, verdict, findings, timings, tokens, cost | `retentionDays` (default 90 days)                          |
| DynamoDB `batches`  | One row per batch: counts, cost, timings                          | `retentionDays`                                            |
| DynamoDB `stats`    | Per-user totals by hour, day and all time                         | Hours 8 days; days and all time until you delete the stack |
| DynamoDB `idempotency` | `POST /scan` Idempotency-Key claims: the caller's key, the URL and the scan id it started | 24 hours (TTL attribute `expires_at`) |
| DynamoDB `phish-cache-{env}` | Result cache: RDAP fields per registered domain and web search result titles, URLs and snippets per brand; never scan content (TTL attribute `ttl`) | RDAP 7 days (`rdapCacheTtlHours`), web search 24 hours (`webSearchCacheTtlHours`) |
| S3 upload bucket | CSV files you uploaded, under `uploads/` | 1 day |
| S3 artifacts bucket | Screenshots, page captures and findings, under `scans/{scan_id}/` | 30 days |
| AgentCore Memory | One line per completed scan: defanged URL, verdict, risk, reason (shared within the deployment as model context; each user is shown only their own matches) | Until you delete the stack (`-c episodicMemory=false` removes it) |

All stores are encrypted with AWS KMS and block public access. Deleting the stack deletes them.

## Why this shape

- **One worker path.** A single scan and a 1,000-URL batch both go through the queue and the same worker, so there is one code path to test and to retry.
- **Three specialists at once, then the orchestrator judges.** Each specialist checks one thing and the orchestrator decides. The Harness runs the tool calls of one turn one after another, so the dispatcher runs the three specialists at the same time and round one costs about the slowest specialist rather than the sum. Current latency and cost are in the [README](../README.md#measured-results) and [evaluation.md](evaluation.md).
- **Verdict first, report second.** The slow part of an Opus answer is the long report, so the orchestrator answers in two turns: two calls on one Harness session by default, two Converse calls on one conversation on the direct path. A failure in turn 2 only marks the report `FAILED`.
- **Dead links skip the models.** The pre-check costs one short browser navigation (and, when the browser cannot answer, one HTTP probe). On a 404 or a site that is down it replaces the whole analysis with a fixed answer.
- **Result cache.** RDAP lookups change rarely and a brand's official site does not change per scan, so both are cached in a small DynamoDB table. The web search TTL is deliberately short (24 hours) to limit cache poisoning; see [security.md](security.md#network).
- **Web search on the tools Gateway.** The Web Search connector is now offered in `us-west-2`, so in the default Region it is a target on `phish-tools` and the scan uses two Gateways, not three. In a Region without the connector the sample falls back to a web search Gateway in its `us-east-1` edge stack (which it already has for the CloudFront web ACL). Either way only `brand_visual` calls it (a client-side allowlist on `phish-tools`, an IAM grant on the fallback Gateway), and queries stay inside AWS. `-c webSearch=false` removes it.
- **Stats computed as you go.** The Insights page reads a few pre-computed rows instead of scanning your history, so it stays fast as history grows.
- **A sweeper that does not grow with history.** Every 5 minutes a sweeper re-queues stuck scans by querying a `status` index for `PENDING` rows, so its cost follows the scans in flight, not the scans stored.
