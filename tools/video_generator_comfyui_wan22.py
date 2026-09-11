from __future__ import annotations

import random
from typing import Any, List

from interfaces.video_output import VideoOutput
from tools.comfyui_client import ComfyUIClient, first_output


class VideoGeneratorComfyUIWan22:
    """Local Wan 2.2 TI2V 5B first-frame video generator through ComfyUI."""

    def __init__(self, base_url="http://127.0.0.1:8188", model="wan2.2_ti2v_5B_fp16.safetensors",
                 clip="umt5_xxl_fp8_e4m3fn_scaled.safetensors", vae="wan2.2_vae.safetensors",
                 width=576, height=1024, length=121, fps=24, steps=20, cfg=5.0,
                 timeout=3600, rate_limiter=None):
        self.client = ComfyUIClient(base_url, timeout)
        self.model, self.clip, self.vae = model, clip, vae
        self.width, self.height, self.length, self.fps = width, height, length, fps
        self.steps, self.cfg = steps, cfg
        self.rate_limiter = rate_limiter

    async def generate_single_video(self, prompt: str = "", reference_image_paths: List[str] | None = None,
                                    aspect_ratio: str = "9:16", **kwargs: Any) -> VideoOutput:
        if self.rate_limiter:
            await self.rate_limiter.acquire()
        refs = list(reference_image_paths or [])
        if not refs:
            raise ValueError("Wan 2.2 I2V requires a first-frame reference image")
        image_name = await self.client.upload_image(refs[0])
        workflow = self._workflow(prompt, image_name, kwargs.get("seed", random.randrange(2**63)),
                                  kwargs.get("width", self.width), kwargs.get("height", self.height),
                                  kwargs.get("length", self.length))
        outputs = await self.client.run(workflow, kwargs.get("progress"))
        # Current ComfyUI SaveVideo reports encoded media under ``images`` with
        # ``animated: true``; older/custom nodes may use ``videos``.
        try:
            descriptor = first_output(outputs, "videos")
        except Exception:
            descriptor = first_output(outputs, "images")
        data = await self.client.download(descriptor)
        return VideoOutput(fmt="bytes", ext="mp4", data=data)

    def _workflow(self, prompt: str, image: str, seed: int, width: int, height: int, length: int) -> dict[str, Any]:
        negative = "blurry, low quality, distorted face, extra limbs, morphing, flicker, style drift, camera shake, text, watermark"
        return {
            "model": {"class_type": "UNETLoader", "inputs": {"unet_name": self.model, "weight_dtype": "default"}},
            "sampling": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["model", 0], "shift": 8.0}},
            "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": self.clip, "type": "wan", "device": "default"}},
            "vae": {"class_type": "VAELoader", "inputs": {"vae_name": self.vae}},
            "positive": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": prompt}},
            "negative": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": negative}},
            "image": {"class_type": "LoadImage", "inputs": {"image": image}},
            "latent": {"class_type": "Wan22ImageToVideoLatent", "inputs": {"vae": ["vae", 0], "start_image": ["image", 0], "width": width, "height": height, "length": length, "batch_size": 1}},
            "sample": {"class_type": "KSampler", "inputs": {"model": ["sampling", 0], "positive": ["positive", 0], "negative": ["negative", 0], "latent_image": ["latent", 0], "seed": int(seed), "steps": self.steps, "cfg": self.cfg, "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1.0}},
            "decode": {"class_type": "VAEDecode", "inputs": {"samples": ["sample", 0], "vae": ["vae", 0]}},
            "video": {"class_type": "CreateVideo", "inputs": {"images": ["decode", 0], "fps": self.fps}},
            "save": {"class_type": "SaveVideo", "inputs": {"video": ["video", 0], "filename_prefix": "ViMax/wan22", "format": "mp4", "codec": "h264"}},
        }
