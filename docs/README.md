# Documentation

**Current results (2026-11-24, 600 URLs, default configuration):**

| Phishing caught | Legitimate sites flagged | Scan time, median | Model cost per scan, median |
| :---: | :---: | :---: | :---: |
| **96.5%** | **4.7%** | **60 s** | **$0.10** |

How these were measured: [README](../README.md#measured-results) and [Evaluation](evaluation.md#current-default-2026-11-24).

Start with [Getting started](getting-started.md) to deploy the sample and run your first scan. The pages below go deeper, in roughly the order you will need them.

| Page | Read it when you want to |
| --- | --- |
| [Getting started](getting-started.md) | Deploy, sign in, scan a URL, call the API, run a batch and clean up |
| [Architecture](architecture.md) | Follow a scan step by step, compare the two orchestration paths, see where data lives |
| [Agents](agents/) | Know what [url_analyst](agents/url_analyst.md), [brand_visual](agents/brand_visual.md), [code_analyst](agents/code_analyst.md), the [orchestrator](agents/orchestrator.md) and the [dispatcher](agents/dispatcher.md) check and decide |
| [API](api.md) | Call the REST API: routes, fields, errors, batches, idempotent retries and lookups |
| [Deploy](deploy.md) | Pick a Region, bootstrap, sign in and MFA, use a custom domain, verify and clean up |
| [Configuration](configuration.md) | Change any deploy option, including each latency flag and what it trades |
| [Tune confidence, risk and actions](customize-verdicts.md) | Match the gate, the orchestrator rules and the caps to your own risk appetite |
| [Evaluation](evaluation.md) | Measure accuracy on your own labelled URLs, and read every measured result |
| [Cost](cost.md) | Estimate idle and per-scan cost by service |
| [Security](security.md) | Review authentication, data protection, network, generative AI controls and IAM |
| [Threat model](threat-model.md) | Review threats and mitigations |
| [Responsible AI](responsible-ai.md) | Understand intended use, limits, the disclaimer and human review |
| [Web app](frontend.md) | Learn the console pages and how they call the API |
| [Troubleshooting](troubleshooting.md) | Fix a deploy, scan or API problem |
| [Architecture diagram](diagram/README.md) | Regenerate the diagram after a change |
| [Demo video script](media/demo-script.md) | Present the sample with the same flow as the demo video |
