# Architecture diagram tooling

`docs/architecture.drawio` is generated. Do not edit it by hand: edit the layout in `build_architecture.py`, then run from the repo root:

```bash
uv run python docs/diagram/build_architecture.py
uv run --with defusedxml==0.7.1 python docs/diagram/validate_diagram.py docs/architecture.drawio
/Applications/draw.io.app/Contents/MacOS/draw.io -x -f png -s 2 -b 20 -o docs/architecture.png docs/architecture.drawio
```

Without the desktop app, the headless container renders the same file (`--shm-size=2g` keeps the renderer from crashing):

```bash
docker run --rm --shm-size=2g -v "$PWD/docs":/data rlespinasse/drawio-desktop-headless:latest -x -f png -s 2 -b 20 -o /data/architecture.png /data/architecture.drawio
```

The validator fails on a diagonal line, a crossing, an overlap, a line through an icon or a long label. The diagram draws the default deploy: the scan path in the scan group with solid, numbered lines (the numbers match the steps in [architecture.md](../architecture.md#how-a-scan-works)), from the pre-check through AgentCore Harness, Gateway `phish-specialists`, the dispatcher, the three specialists, Gateway `phish-tools` and the tools server to AgentCore Browser. `brand_visual`'s web search is the one dashed line, and anything off the scan path sits in the supporting services group with no lines. The opt-in direct path (`-c directOrchestration=true`) is named in the footer, and AWS Agent Registry is labelled off by default, because it is deployed only with `-c agentRegistry=true`. Icons: AWS Architecture Icons release 07312026.

All icons are draw.io built-ins (`mxgraph.aws4`). The 07312026 package has no separate AgentCore Harness, Runtime, Gateway or Browser icons, so AgentCore Harness, both Gateways, the dispatcher, the specialists, the tools server, AgentCore Browser, AgentCore Memory, AgentCore Web Search and the AWS Agent Registry (part of Amazon Bedrock AgentCore) use `bedrock_agentcore` and are told apart by label. No icon files are committed.
