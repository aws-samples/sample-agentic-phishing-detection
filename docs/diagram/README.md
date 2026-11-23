# Architecture diagram tooling

`docs/architecture.drawio` is generated. Do not edit it by hand: edit the layout in `build_architecture.py`, then run from the repo root:

```bash
uv run python docs/diagram/build_architecture.py
uv run --with defusedxml==0.7.1 python docs/diagram/validate_diagram.py docs/architecture.drawio
/Applications/draw.io.app/Contents/MacOS/draw.io -x -f png -s 2 -b 20 -o docs/architecture.png docs/architecture.drawio
```

Without the desktop app, the headless container renders the same file (`--shm-size=2g` keeps the renderer from crashing):

```bash
docker run --rm --shm-size=2g -v "$PWD/docs":/data rlespinasse/drawio-desktop-headless@sha256:95f6c9cec1346592a3122b4d8c2e1008a92cb36276e3a657cdb74524ba1f0fcb -x -f png -s 2 -b 20 -o /data/architecture.png /data/architecture.drawio
```

The validator fails on a diagonal line, a crossing, an overlap, a line through an icon or a long label. The diagram draws the default deploy: the scan path in the scan group with solid, numbered lines (the numbers match the steps in [architecture.md](../architecture.md#how-a-scan-works)), from the pre-check through AgentCore Harness and the two Gateways to AgentCore Browser. Each AgentCore Gateway is a box with its targets inside: `phish-specialists` holds the dispatcher Lambda target and the three specialists, boxed as agents exposed as MCP tools (agents as tools, not A2A); `phish-tools` holds the tools MCP server and AgentCore Web Search. A line that crosses a Gateway box border is a call through that Gateway, except the pre-check, which the worker sends to the tools MCP server directly (its label says so). Two lines are dashed: `brand_visual`'s web search and the optional second round, in which the orchestrator calls one specialist again. Anything off the scan path sits in the supporting services group with no lines. The opt-in direct path (`-c directOrchestration=true`) is named in the footer, and AWS Agent Registry is labelled off by default, because it is deployed only with `-c agentRegistry=true`. The fallback web search Gateway in the edge stack (only for a Region without the Web Search connector) is not drawn. Icons: AWS Architecture Icons release 07312026.

The Gateway boxes are plain boxes drawn behind the icons, not icons, so the validator lets lines cross their borders; the boxes are separate cells with absolute coordinates, because the validator does not support nested cells.

All icons are draw.io built-ins (`mxgraph.aws4`). The 07312026 package has no separate AgentCore Harness, Runtime, Gateway or Browser icons, so AgentCore Harness, the specialists, the tools MCP server, AgentCore Browser, AgentCore Memory, AgentCore Web Search and the AWS Agent Registry (part of Amazon Bedrock AgentCore) use `bedrock_agentcore` and are told apart by label. The worker and the dispatcher use the AWS Lambda icon. No icon files are committed.
