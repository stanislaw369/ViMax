from __future__ import annotations

import io
import random
from typing import Any, List

from PIL import Image

from interfaces.image_output import ImageOutput
from tools.comfyui_client import ComfyUIClient, first_output


class ImageGeneratorComfyUIFlux2:
    """Local Flux.2 Klein generator/editor using one or more reference images."""

    def __init__(self, base_url="http://127.0.0.1:8188", model="flux-2-klein-base-4b.safetensors",
                 clip="qwen_3_4b.safetensors", vae="flux2-vae.safetensors", steps=20,
                 cfg=4.0, denoise=1.0, width=576, height=1024, timeout=1800, rate_limiter=None):
        self.client = ComfyUIClient(base_url, timeout)
        self.model, self.clip, self.vae = model, clip, vae
        self.steps, self.cfg, self.denoise = steps, cfg, denoise
        self.width, self.height = width, height
        self.rate_limiter = rate_limiter

    async def generate_single_image(self, prompt: str, reference_image_paths: List[str] | None = None,
                                    aspect_ratio: str | None = "9:16", **kwargs: Any) -> ImageOutput:
        if self.rate_limiter:
            await self.rate_limiter.acquire()
        refs = list(reference_image_paths or [])
        width, height = _dimensions(kwargs.get("size"), kwargs.get("width", self.width), kwargs.get("height", self.height))
        workflow = self._workflow(prompt, width, height, kwargs.get("seed", random.randrange(2**63)), refs)
        for index, path in enumerate(refs):
            workflow[f"load_ref_{index}"]["inputs"]["image"] = await self.client.upload_image(path)
        outputs = await self.client.run(workflow, kwargs.get("progress"))
        data = await self.client.download(first_output(outputs, "images"))
        with Image.open(io.BytesIO(data)) as opened:
            opened.load()
            image = opened.copy()
        return ImageOutput(fmt="pil", ext="png", data=image)

    def _workflow(self, prompt: str, width: int, height: int, seed: int, refs: list[str]) -> dict[str, Any]:
        w: dict[str, Any] = {
            "model": {"class_type": "UNETLoader", "inputs": {"unet_name": self.model, "weight_dtype": "default"}},
            "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": self.clip, "type": "flux2", "device": "default"}},
            "vae": {"class_type": "VAELoader", "inputs": {"vae_name": self.vae}},
            "positive": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["clip", 0]}},
            "negative": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["clip", 0]}},
            "latent": {"class_type": "EmptySD3LatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
            "sampler": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
            "scheduler": {"class_type": "Flux2Scheduler", "inputs": {"steps": self.steps, "width": width, "height": height}},
            "sigmas": {"class_type": "SplitSigmasDenoise", "inputs": {"sigmas": ["scheduler", 0], "denoise": self.denoise}},
            "noise": {"class_type": "RandomNoise", "inputs": {"noise_seed": int(seed)}},
        }
        positive: list[Any] = ["positive", 0]
        for index, _ in enumerate(refs):
            load, encode, ref = f"load_ref_{index}", f"encode_ref_{index}", f"reference_{index}"
            w[load] = {"class_type": "LoadImage", "inputs": {"image": ""}}
            w[encode] = {"class_type": "VAEEncode", "inputs": {"pixels": [load, 0], "vae": ["vae", 0]}}
            w[ref] = {"class_type": "ReferenceLatent", "inputs": {"conditioning": positive, "latent": [encode, 0]}}
            positive = [ref, 0]
        w.update({
            "guider": {"class_type": "CFGGuider", "inputs": {"cfg": self.cfg, "model": ["model", 0], "positive": positive, "negative": ["negative", 0]}},
            "sample": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["noise", 0], "guider": ["guider", 0], "sampler": ["sampler", 0], "sigmas": ["sigmas", 1], "latent_image": ["latent", 0]}},
            "decode": {"class_type": "VAEDecode", "inputs": {"samples": ["sample", 0], "vae": ["vae", 0]}},
            "save": {"class_type": "SaveImage", "inputs": {"images": ["decode", 0], "filename_prefix": "ViMax/flux2"}},
        })
        return w


def _dimensions(size: Any, width: int, height: int) -> tuple[int, int]:
    if isinstance(size, str) and "x" in size:
        left, right = size.lower().split("x", 1)
        width, height = int(left), int(right)
    return max(64, width // 16 * 16), max(64, height // 16 * 16)
