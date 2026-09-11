from __future__ import annotations

import asyncio
import json
import mimetypes
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import aiohttp


class ComfyUIError(RuntimeError):
    pass


class ComfyUIClient:
    """Small async client for ComfyUI's local prompt API."""

    def __init__(self, base_url: str = "http://127.0.0.1:8188", timeout: float = 1800.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client_id = str(uuid.uuid4())

    async def upload_image(self, path: str) -> str:
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(source)
        form = aiohttp.FormData()
        form.add_field(
            "image",
            source.read_bytes(),
            filename=source.name,
            content_type=mimetypes.guess_type(source.name)[0] or "application/octet-stream",
        )
        form.add_field("overwrite", "true")
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
            async with session.post(f"{self.base_url}/upload/image", data=form) as response:
                payload = await response.json(content_type=None)
                if response.status >= 400:
                    raise ComfyUIError(f"Image upload failed ({response.status}): {payload}")
        subfolder = payload.get("subfolder", "")
        return f"{subfolder}/{payload['name']}" if subfolder else payload["name"]

    async def run(self, workflow: dict[str, Any], progress=None) -> dict[str, Any]:
        body = {"prompt": workflow, "client_id": self.client_id}
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
            async with session.post(f"{self.base_url}/api/prompt", json=body) as response:
                payload = await response.json(content_type=None)
                if response.status >= 400 or "prompt_id" not in payload:
                    raise ComfyUIError(f"Prompt rejected ({response.status}): {json.dumps(payload)}")
        prompt_id = payload["prompt_id"]
        if progress:
            progress("comfyui_queued", "ComfyUI prompt queued", {"prompt_id": prompt_id})
        deadline = asyncio.get_running_loop().time() + self.timeout
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(2)
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(f"{self.base_url}/history/{prompt_id}") as response:
                    history = await response.json(content_type=None)
            item = history.get(prompt_id)
            if not item:
                continue
            status = item.get("status", {})
            if status.get("status_str") == "error":
                raise ComfyUIError(f"Prompt failed: {json.dumps(status)}")
            if status.get("completed") or status.get("status_str") == "success":
                return item.get("outputs", {})
        raise TimeoutError(f"ComfyUI prompt {prompt_id} exceeded {self.timeout:g}s")

    async def download(self, descriptor: dict[str, Any]) -> bytes:
        params = urlencode({
            "filename": descriptor["filename"],
            "subfolder": descriptor.get("subfolder", ""),
            "type": descriptor.get("type", "output"),
        })
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
            async with session.get(f"{self.base_url}/api/view?{params}") as response:
                data = await response.read()
                if response.status >= 400:
                    raise ComfyUIError(f"Output download failed ({response.status}): {data[:500]!r}")
                return data


def first_output(outputs: dict[str, Any], key: str) -> dict[str, Any]:
    for node in outputs.values():
        values = node.get(key)
        if values:
            return values[0]
    raise ComfyUIError(f"ComfyUI result contains no {key}: {json.dumps(outputs)[:2000]}")
