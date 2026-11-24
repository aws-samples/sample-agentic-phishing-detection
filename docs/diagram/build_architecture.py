# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Generate docs/architecture.drawio from a layout spec.

Coordinates are absolute and on a strict grid. Every edge has explicit ports and waypoints and
edgeStyle=none, so validate_diagram.py checks exactly what draw.io draws. Labels sit under icons
(above for LABEL_TOP), so edges leave icons from the other sides. Edit the tables, then run:
  uv run python docs/diagram/build_architecture.py
  uv run --with defusedxml==0.7.1 python docs/diagram/validate_diagram.py docs/architecture.drawio
"""

from pathlib import Path

# The diagram is written by the small serializer below rather than xml.etree: this script
# only emits XML built from the tables in this file and never parses any, and keeping the
# stdlib XML package out entirely means no parser that could expand entities is even
# importable here. validate_diagram.py reads the file back with defusedxml.
ATTR_ESCAPES = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "\n": "&#10;"}
ATTR_ESCAPES |= {"\r": "&#13;", "\t": "&#09;"}


class Element:
    """An XML element with attributes and children, serialized like ElementTree does."""

    def __init__(self, tag: str, /, **attrib: str) -> None:
        self.tag, self.attrib, self.children = tag, attrib, []

    def to_xml(self, depth: int = 0) -> str:
        pad = "  " * depth
        attrs = "".join(
            f' {k}="{"".join(ATTR_ESCAPES.get(c, c) for c in v)}"' for k, v in self.attrib.items()
        )
        if not self.children:
            return f"{pad}<{self.tag}{attrs} />"
        inner = "\n".join(child.to_xml(depth + 1) for child in self.children)
        return f"{pad}<{self.tag}{attrs}>\n{inner}\n{pad}</{self.tag}>"


def SubElement(parent: Element, tag: str, /, **attrib: str) -> Element:  # noqa: N802 - ET name
    child = Element(tag, **attrib)
    parent.children.append(child)
    return child


OUT = Path(__file__).resolve().parents[1] / "architecture.drawio"
ICON = 64
INK = "#232F3E"
# The README shows the PNG about 900 px wide, so text is large on this canvas.
FONT, EDGE_FONT, GROUP_FONT = 16, 15, 18

# AWS Architecture Icons 07312026 category colors.
COLOR = {
    "compute": "#ED7100",
    "storage": "#7AA116",
    "database": "#C925D1",
    "integration": "#E7157B",
    "networking": "#8C4FFF",
    "ml": "#01A88D",
}

# Default deploy only (agentRegistry=false, webSearch=true, browserSigning=false,
# episodicMemory=true, every path flag off). Each AgentCore Gateway is drawn as a box with its
# targets inside, and a line that crosses a Gateway box border is a call through that Gateway.
# The scan row runs left to right in step order: Harness, Gateway phish-specialists (the
# dispatcher Lambda target and the three specialist agents, exposed as MCP tools), Gateway
# phish-tools (the tools MCP server and AgentCore Web Search), AgentCore Browser. The worker sits
# above the tools MCP server, so the pre-check drops straight down; its Harness line runs left in
# its own lane. Every explanation lives in the numbered steps in docs/architecture.md, so line
# labels stay at three words or fewer.
X_HARNESS, X_DISP, X_SPEC = 120, 360, 640  # icon centers on the scan row
X_WS, X_TOOLS, X_BROWSER = 990, 1190, 1440
ROW1 = 80  # request path icon tops
SPEC_PITCH = 140  # vertical pitch of the three specialists
ROWM = 530  # the scan row (middle specialist) icon top
ROW_UP, ROW_DOWN = ROWM - SPEC_PITCH, ROWM + SPEC_PITCH  # brand_visual, code_analyst
SUPPORT = 950
LANE_TOP = ROW1 - 35  # the direct API client line
LANE_HARNESS = 210  # the worker to Harness line
LANE_ROUND2 = ROW_DOWN + ICON + 66  # the optional second round runs under the specialists
ROUND2_X = X_HARNESS + 90  # its drop clears the Harness label
TOOLS_X = 860  # the brand_visual and code_analyst tool lines turn here, between the Gateways
PAGE_W, PAGE_H = 1560, 1180
GROUP_W = PAGE_W - 40
SUP_PITCH = 250  # six supporting services share the row
SUP = [120 + i * SUP_PITCH for i in range(6)]


def at(x: int) -> int:
    """Icon left edge for an icon center."""
    return x - ICON // 2


def sup(i: int) -> int:
    """Icon left edge for a supporting services slot."""
    return SUP[i] - ICON // 2


# (label, x, y, w, h, border color, label align). Labels sit at the bottom.
GROUPS = [
    ("The scan: Amazon Bedrock and AgentCore", 20, 245, GROUP_W, 640, "#01A88D", "right"),
    ("Supporting services (no lines)", 20, 920, GROUP_W, 190, "#7D8998", "left"),
]

# Boxes drawn behind icons, label at the top: (id, label, x, y, w, h, fill, label align).
# The two Gateways hold their targets; the specialists box inside phish-specialists names the
# agents-as-tools pattern (MCP tools on the Gateway, not A2A agents).
SPEC_BOX = (X_SPEC - 120, ROW_UP - 62, 240, 2 * SPEC_PITCH + ICON + 62 + 40)
GW_SPEC = (X_DISP - 120, SPEC_BOX[1] - 42, SPEC_BOX[0] + SPEC_BOX[2] + 30 - (X_DISP - 120), 0)
GW_SPEC = (*GW_SPEC[:3], LANE_ROUND2 + 30 - GW_SPEC[1])
GW_TOOLS = (X_WS - 90, ROW_UP - 42, X_TOOLS + 100 - (X_WS - 90), ROWM + ICON + 76 - (ROW_UP - 42))
BOXES = [
    ("gw_spec", "Gateway phish-specialists (MCP)", *GW_SPEC, "#FFFFFF", "left"),
    ("gw_tools", "Gateway phish-tools (MCP)", *GW_TOOLS, "#FFFFFF", "left"),
    ("specialists", "Agents as tools (MCP)\n3 specialists, Sonnet", *SPEC_BOX, "#F2FBF9", "center"),
]


def frac(box: tuple, y: float) -> float:
    """Entry port on a box's left side, level with y."""
    return round((y - box[1]) / box[3], 4)


# id: (label, resIcon, category, x, y). "user" is the general user shape. Two lines at most.
NODES = {
    "client": ("Users and\nAPI clients", "user", "", at(120), ROW1),
    "cf": ("CloudFront\n+ AWS WAF", "cloudfront", "networking", at(340), ROW1),
    "api": ("API Gateway\n+ Lambda (API)", "api_gateway", "integration", at(560), ROW1),
    "sqs": ("Amazon SQS\nscan queue", "sqs", "integration", at(880), ROW1),
    "worker": ("AWS Lambda\nworker", "lambda", "compute", at(X_TOOLS), ROW1),
    "harness": (
        "AgentCore Harness\norchestrator (Opus)",
        "bedrock_agentcore",
        "ml",
        at(X_HARNESS),
        ROWM,
    ),
    "dispatcher": ("dispatcher Lambda\n(no model)", "lambda", "compute", at(X_DISP), ROWM),
    "rt_brand": ("brand_visual", "bedrock_agentcore", "ml", at(X_SPEC), ROW_UP),
    "rt_url": ("url_analyst", "bedrock_agentcore", "ml", at(X_SPEC), ROWM),
    "rt_code": ("code_analyst", "bedrock_agentcore", "ml", at(X_SPEC), ROW_DOWN),
    "websearch": ("AgentCore\nWeb Search", "bedrock_agentcore", "ml", at(X_WS), ROW_UP),
    "tools": ("tools MCP server\n(RDAP, no model)", "bedrock_agentcore", "ml", at(X_TOOLS), ROWM),
    "browser": ("AgentCore\nBrowser", "bedrock_agentcore", "ml", at(X_BROWSER), ROWM),
    # Supporting services: no lines; the steps in docs/architecture.md say who uses each.
    "ddb": ("DynamoDB\nscans", "dynamodb", "database", sup(0), SUPPORT),
    "artifacts": ("Amazon S3\nartifacts", "s3", "storage", sup(1), SUPPORT),
    "cache": ("DynamoDB\nresult cache", "dynamodb", "database", sup(2), SUPPORT),
    "memory": ("AgentCore\nMemory", "bedrock_agentcore", "ml", sup(3), SUPPORT),
    "guardrails": ("Bedrock\nGuardrails", "bedrock", "ml", sup(4), SUPPORT),
    "registry": ("Agent Registry\n(opt-in, off)", "bedrock_agentcore", "ml", sup(5), SUPPORT),
}
# Lines leave these icons downwards, so their labels sit above.
LABEL_TOP = {"worker"}

# Plain text, no border, not an obstacle: (id, text, x, y, w, h). The legend.
TEXTS = [
    (
        "footer",
        "Solid lines: the scan path, numbered in order (docs/architecture.md explains each "
        "step); the pre-check runs before any model and calls the tools MCP server directly. "
        "Any other line into a Gateway box is a call through that Gateway to the target it "
        "ends on. Dashed: the optional second round "
        "(one specialist) and brand_visual's web search. Bottom row: off the path, no lines.\n"
        "Opt-in direct path (-c directOrchestration=true): the worker calls the specialists and "
        "Opus itself. Every AWS call is signed with SigV4.",
        20,
        1118,
        GROUP_W,
        44,
    ),
]

MID = ROWM + ICON / 2
# id: (source, target, exit (x, y), entry (x, y), waypoints, label[, "dashed"][, label position])
# The label position runs from -1 (source) to 1 (target); the default 0 is the middle.
EDGES = {
    "client_cf": ("client", "cf", (1, 0.5), (0, 0.5), [], "1 HTTPS"),
    "client_api": (
        "client",
        "api",
        (0.5, 0),
        (0.5, 0),
        [(120, LANE_TOP), (560, LANE_TOP)],
        "1 SigV4",
    ),
    "cf_api": ("cf", "api", (1, 0.5), (0, 0.5), [], "SigV4"),
    "api_sqs": ("api", "sqs", (1, 0.5), (0, 0.5), [], "2 enqueue"),
    "sqs_worker": ("sqs", "worker", (1, 0.5), (0, 0.5), [], "2 trigger"),
    "worker_precheck": ("worker", "tools", (0.75, 1), (0.75, 0), [], "3 direct pre-check", -0.15),
    "worker_harness": (
        "worker",
        "harness",
        (0.25, 1),
        (0.5, 0),
        [(X_TOOLS - ICON / 4, LANE_HARNESS), (X_HARNESS, LANE_HARNESS)],
        "4 invoke",
    ),
    "harness_dispatcher": ("harness", "dispatcher", (1, 0.5), (0, 0.5), [], "5 analyze_all"),
    "dispatcher_specs": (
        "dispatcher",
        "specialists",
        (1, 0.5),
        (0, frac(SPEC_BOX, MID)),
        [],
        "6 parallel",
    ),
    "harness_round2": (
        "harness",
        "specialists",
        (1, 0.75),
        (0.5, 1),
        [(ROUND2_X, ROWM + 3 * ICON / 4), (ROUND2_X, LANE_ROUND2), (X_SPEC, LANE_ROUND2)],
        "round 2",
        "dashed",
        0.3,
    ),
    "brand_tools": (
        "rt_brand",
        "tools",
        (1, 0.75),
        (0, 0.25),
        [(TOOLS_X, ROW_UP + 3 * ICON / 4), (TOOLS_X, ROWM + ICON / 4)],
        "",
    ),
    "url_tools": ("rt_url", "tools", (1, 0.5), (0, 0.5), [], "7 tools", -0.35),
    "code_tools": (
        "rt_code",
        "tools",
        (1, 0.25),
        (0, 0.75),
        [(TOOLS_X, ROW_DOWN + ICON / 4), (TOOLS_X, ROWM + 3 * ICON / 4)],
        "",
    ),
    "brand_search": ("rt_brand", "websearch", (1, 0.25), (0, 0.25), [], "search", "dashed", 0.2),
    "tools_browser": ("tools", "browser", (1, 0.5), (0, 0.5), [], "8 browse"),
}

LABEL = f"align=center;html=0;fontSize={FONT};fontColor={INK};whiteSpace=nowrap;"
LABEL_BELOW = "verticalLabelPosition=bottom;verticalAlign=top;" + LABEL
LABEL_ABOVE = "verticalLabelPosition=top;verticalAlign=bottom;" + LABEL


def icon_style(cid: str, icon: str, category: str) -> str:
    label = LABEL_ABOVE if cid in LABEL_TOP else LABEL_BELOW
    if icon == "user":
        return f"shape=mxgraph.aws4.user;fillColor={INK};strokeColor=none;aspect=fixed;" + label
    return (
        f"shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{icon};fillColor={COLOR[category]};"
        "strokeColor=#ffffff;outlineConnect=0;aspect=fixed;" + label
    )


def _cell(root: Element, cid: str, value: str, style: str, x: int, y: int, w: int, h: int) -> None:
    cell = SubElement(root, "mxCell", id=cid, value=value, vertex="1", parent="1", style=style)
    SubElement(
        cell, "mxGeometry", x=str(x), y=str(y), width=str(w), height=str(h), **{"as": "geometry"}
    )


def _edge(root: Element, cid: str, spec: tuple) -> None:
    src, tgt, (ex, ey), (nx, ny), points, label, *extra = spec
    style = (
        "edgeStyle=none;rounded=0;html=0;endArrow=block;endFill=1;strokeColor=#545B64;"
        f"strokeWidth=2;exitX={ex};exitY={ey};exitDx=0;exitDy=0;"
        f"entryX={nx};entryY={ny};entryDx=0;entryDy=0;"
        f"fontSize={EDGE_FONT};fontColor={INK};labelBackgroundColor=#ffffff;"
        + ("dashed=1;dashPattern=6 4;" if "dashed" in extra else "")
    )
    cell = SubElement(
        root,
        "mxCell",
        id=cid,
        value=label,
        edge="1",
        parent="1",
        source=src,
        target=tgt,
        style=style,
    )
    pos = [str(e) for e in extra if isinstance(e, float)]
    geo = SubElement(
        cell, "mxGeometry", relative="1", **({"x": pos[0]} if pos else {}), **{"as": "geometry"}
    )
    if points:
        arr = SubElement(geo, "Array", **{"as": "points"})
        for x, y in points:
            SubElement(arr, "mxPoint", x=str(x), y=str(y))


def build() -> Element:
    mxfile = Element("mxfile", host="drawio", compressed="false")
    diagram = SubElement(mxfile, "diagram", id="architecture", name="Architecture")
    model = SubElement(
        diagram,
        "mxGraphModel",
        dx=str(PAGE_W),
        dy=str(PAGE_H),
        grid="1",
        gridSize="10",
        page="1",
        pageWidth=str(PAGE_W),
        pageHeight=str(PAGE_H),
        background="#FFFFFF",
    )
    root = SubElement(model, "root")
    SubElement(root, "mxCell", id="0")
    SubElement(root, "mxCell", id="1", parent="0")

    for i, (label, x, y, w, h, color, *opt) in enumerate(GROUPS):
        _cell(
            root,
            f"group{i}",
            label,
            (
                "rounded=0;dashed=1;dashPattern=4 4;fillColor=none;"
                f"strokeColor={color};strokeWidth=2;verticalAlign=bottom;"
                f"align={opt[0] if opt else 'left'};fontSize={GROUP_FONT};fontStyle=1;"
                f"fontColor={color};spacingLeft=10;spacingRight=10;spacingBottom=4;"
            ),
            x,
            y,
            w,
            h,
        )

    for cid, label, x, y, w, h, fill, align in BOXES:
        _cell(
            root,
            cid,
            label,
            (
                f"rounded=1;arcSize=4;fillColor={fill};strokeColor=#01A88D;strokeWidth=1;"
                f"verticalAlign=top;align={align};fontSize={FONT};fontStyle=1;fontColor=#01A88D;"
                "spacingTop=4;spacingLeft=10;whiteSpace=nowrap;"
            ),
            x,
            y,
            w,
            h,
        )

    for cid, (label, icon, category, x, y) in NODES.items():
        _cell(root, cid, label, icon_style(cid, icon, category), x, y, ICON, ICON)

    for cid, text, x, y, w, h in TEXTS:
        _cell(
            root,
            cid,
            text,
            (
                f"text;html=0;fillColor=none;strokeColor=none;fontSize={FONT - 2};"
                f"fontColor={INK};align=left;verticalAlign=top;whiteSpace=wrap;"
            ),
            x,
            y,
            w,
            h,
        )

    for cid, spec in EDGES.items():
        _edge(root, cid, spec)
    return mxfile


if __name__ == "__main__":
    OUT.write_text(build().to_xml(), encoding="utf-8")
    print(f"wrote {OUT}")
