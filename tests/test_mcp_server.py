#!/usr/bin/env python3
"""
End-to-end MCP test: launches mcp_server.py over stdio and drives it as a client.

Run with:  python3 tests/test_mcp_server.py

Covers the tool contract, the sandbox and resource guards, and the schema
constraints that keep the server usable from clients whose JSON Schema support
is narrower than Claude's.
"""

import asyncio
import base64
import os
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parent.parent
FAILURES = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}{('  -- ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(name)


def text_of(result):
    return "\n".join(c.text for c in result.content if c.type == "text")


def has_image(result):
    return any(c.type == "image" for c in result.content)


def find_unions(node, path="root"):
    """
    Locate anyOf/oneOf/allOf anywhere in a schema.

    Gemini's function-declaration schema is an OpenAPI subset that has not
    reliably accepted these, so both input and output schemas must stay free of
    them for the server to be callable everywhere.
    """
    hits = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("anyOf", "oneOf", "allOf"):
                hits.append(f"{path}.{key}")
            hits += find_unions(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            hits += find_unions(value, f"{path}[{i}]")
    return hits


def make_fixtures(work):
    face = Image.new("RGB", (900, 1200), "white")
    draw = ImageDraw.Draw(face)
    draw.rectangle([0, 0, 899, 1199], outline=(255, 0, 0), width=12)
    draw.ellipse([250, 300, 650, 800], fill=(80, 140, 220))
    face.save(work / "face.jpg", quality=95)
    for i, colour in enumerate([(200, 50, 50), (50, 200, 50), (50, 50, 200), (200, 200, 50)]):
        Image.new("RGB", (1600, 900), colour).save(work / f"pic{i}.jpg", quality=95)


async def run(work, outside):
    python = REPO / "venv/bin/python"
    params = StdioServerParameters(
        command=str(python if python.exists() else Path(sys.executable)),
        args=[str(REPO / "mcp_server.py"), "--base-dir", str(work)],
        env={**os.environ},
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            check("server initializes over stdio", True, init.serverInfo.name)

            tools = (await session.list_tools()).tools
            names = sorted(t.name for t in tools)
            check("exposes the 3 expected tools",
                  names == ["create_collage", "create_photo_grid", "inspect_image"], str(names))

            for tool in tools:
                hits = find_unions(tool.inputSchema) + find_unions(tool.outputSchema or {})
                check(f"{tool.name} schemas contain no anyOf/oneOf/allOf", not hits, str(hits))
                check(f"{tool.name} carries a usable description",
                      bool(tool.description and len(tool.description) > 40))

            # inspect_image
            result = await session.call_tool("inspect_image", {"image_path": "face.jpg"})
            body = text_of(result)
            check("inspect_image reports orientation and crop loss",
                  "portrait" in body and "300 px" in body)

            # photo grid from a path
            result = await session.call_tool(
                "create_photo_grid", {"image_path": "face.jpg", "edging_mm": 0.5})
            body = text_of(result)
            check("create_photo_grid succeeds", not result.isError, body.splitlines()[0] if body else "")
            check("grid reports zero clipped copies", "Clipped copies: 0" in body)
            check("grid explains the downsizing", "edging_mm=0" in body)
            check("grid output written", (work / "face_grid.jpg").exists())

            # exact 2x2 for passport use
            result = await session.call_tool(
                "create_photo_grid",
                {"image_path": "face.jpg", "edging_mm": 0, "output_path": "exact.jpg"})
            check("edging_mm=0 gives exact 2.000x2.000 inch photos",
                  "2.000x2.000 inches" in text_of(result))

            # overwrite guard
            result = await session.call_tool(
                "create_photo_grid", {"image_path": "face.jpg", "edging_mm": 0.5})
            check("refuses to overwrite silently",
                  result.isError and "already exists" in text_of(result))
            result = await session.call_tool(
                "create_photo_grid",
                {"image_path": "face.jpg", "edging_mm": 0.5, "overwrite": True})
            check("overwrite=true permitted", not result.isError)

            # base64 input, for clients that attach rather than pass paths
            blob = base64.b64encode((work / "face.jpg").read_bytes()).decode()
            result = await session.call_tool(
                "create_photo_grid", {"image_base64": blob, "output_path": "from_b64.jpg"})
            check("create_photo_grid accepts base64 input", not result.isError)
            check("base64 output written", (work / "from_b64.jpg").exists())

            result = await session.call_tool("create_photo_grid", {})
            check("rejects neither path nor base64",
                  result.isError and "exactly one" in text_of(result))
            result = await session.call_tool(
                "create_photo_grid", {"image_path": "face.jpg", "image_base64": blob})
            check("rejects both path and base64",
                  result.isError and "exactly one" in text_of(result))

            # collage, both layouts
            paths = [f"pic{i}.jpg" for i in range(4)]
            result = await session.call_tool(
                "create_collage",
                {"image_paths": paths, "output_path": "c_grid.jpg", "resize": True})
            check("create_collage grid layout",
                  not result.isError and "Images placed: 4" in text_of(result))
            result = await session.call_tool(
                "create_collage",
                {"image_paths": paths, "output_path": "c_rand.jpg", "layout": "random"})
            check("create_collage random layout with resize=false", not result.isError,
                  text_of(result)[:70] if result.isError else "")

            pic_blob = base64.b64encode((work / "pic0.jpg").read_bytes()).decode()
            result = await session.call_tool(
                "create_collage",
                {"image_paths": ["pic1.jpg"], "images_base64": [pic_blob],
                 "output_path": "c_mixed.jpg", "resize": True})
            check("collage mixes paths and base64",
                  not result.isError and "Images placed: 2" in text_of(result))

            # preview is opt-in, because image block support varies by client
            result = await session.call_tool(
                "create_collage",
                {"image_paths": paths, "output_path": "c_prev.jpg",
                 "resize": True, "return_preview": True})
            check("return_preview yields an image content block",
                  has_image(result) and bool(text_of(result)))
            result = await session.call_tool(
                "create_collage",
                {"image_paths": paths, "output_path": "c_noprev.jpg", "resize": True})
            check("preview off by default", not has_image(result))

            # guards
            result = await session.call_tool(
                "create_collage", {"image_paths": paths, "output_path": "x.jpg", "dpi": 5000})
            check("rejects dpi above the cap",
                  result.isError and "dpi must be" in text_of(result))
            result = await session.call_tool(
                "create_photo_grid",
                {"image_path": os.path.relpath(outside, work), "output_path": "esc.jpg"})
            check("rejects input escaping the base directory",
                  result.isError and "outside the allowed" in text_of(result))
            result = await session.call_tool(
                "create_photo_grid",
                {"image_path": "face.jpg", "output_path": "../escape_out.jpg"})
            check("rejects output escaping the base directory",
                  result.isError and "outside the allowed" in text_of(result))
            result = await session.call_tool("create_photo_grid", {"image_path": "ghost.jpg"})
            check("missing file returns a tool error",
                  result.isError and "not found" in text_of(result))
            result = await session.call_tool(
                "create_collage",
                {"image_paths": paths, "output_path": "y.jpg", "layout": "spiral"})
            check("rejects unknown layout",
                  result.isError and "must be 'grid' or 'random'" in text_of(result))
            result = await session.call_tool(
                "create_photo_grid", {"image_base64": "not-base64!!", "output_path": "z.jpg"})
            check("rejects malformed base64",
                  result.isError and "base64" in text_of(result))

            result = await session.call_tool("inspect_image", {"image_path": "pic0.jpg"})
            check("server still responsive after every error path", not result.isError)

            # tools are async and offloaded; sync tools would serialise on the loop
            results = await asyncio.gather(*[
                session.call_tool(
                    "create_collage",
                    {"image_paths": paths, "output_path": f"conc{i}.jpg", "resize": True})
                for i in range(4)
            ])
            check("4 concurrent renders all succeed", all(not r.isError for r in results))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        work = root / "work"
        work.mkdir()
        make_fixtures(work)
        outside = root / "outside.jpg"
        outside.write_bytes((work / "face.jpg").read_bytes())
        asyncio.run(run(work, outside))

    print()
    if FAILURES:
        print(f"FAILURES ({len(FAILURES)}): {FAILURES}")
        return 1
    print("All MCP server tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
