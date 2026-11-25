import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile


async def verify(folder):
    import tkinter

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    from ma_ru.accounts import vault

    assert tkinter.Tcl().eval("info patchlevel")
    assert vault().priority > 0
    config = json.loads((folder / "mcp.json").read_bytes())
    for entry in config["mcpServers"].values():
        command = (folder / entry["command"]).resolve()
        assert command == Path(sys.executable).resolve()
        params = StdioServerParameters(command=str(command), args=entry["args"])
        async with stdio_client(params) as (r, w), ClientSession(r, w) as session:
            await session.initialize()
            names = {tool.name for tool in (await session.list_tools()).tools}
            assert {
                "poll_new",
                "prepare_reply",
                "mailbox_overview",
                "poll_mailboxes",
                "set_folder_rule",
                "route_attachments",
                "read_message",
                "modify_messages",
                "send_email",
            } <= names
            print(f"Standalone plugin returned {len(names)} tools.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(verify(Path(sys.argv[1])))
    else:
        root = Path(__file__).resolve().parents[1]
        version = json.loads((root / "plugins/ma-ru/plugin.json").read_bytes())[
            "version"
        ]
        archive = root / "dist" / f"ma-ru-{version}-windows-x64.zip"
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Ma Ru QA"
            with ZipFile(archive) as z:
                assert not any(p.endswith("direct_url.json") for p in z.namelist())
                assert {
                    "connect.cmd",
                    "runtime/LICENSE.txt",
                    "assets/envelope.svg",
                    "NOTICE",
                } <= set(z.namelist())
                z.extractall(folder)
            subprocess.run(
                [folder / "runtime/python.exe", "-I", "-B", __file__, folder],
                check=True,
                timeout=90,
            )
