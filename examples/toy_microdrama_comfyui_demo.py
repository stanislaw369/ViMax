"""Controlled 15-second ViMax renderer smoke test for Flux.2 + Wan 2.2.

This intentionally bypasses an external planning LLM: the story and shot plan are
fixed so the test measures local visual continuity rather than prompt variance.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path

from tools import ImageGeneratorComfyUIFlux2, VideoGeneratorComfyUIWan22


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".working_dir" / "toy_microdrama_comfyui_demo"

STYLE = (
    "premium cinematic stop-motion toy-doll microdrama, realistic handcrafted 1:6 scale dolls, "
    "subtle molded vinyl faces, detailed miniature clothing and apartment set, dramatic soft practical lighting, "
    "shallow depth of field, restrained serious acting, coherent character design, vertical 9:16, "
    "no text, no watermark, no split screen, not cute, not anime, not live-action humans"
)


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    image = ImageGeneratorComfyUIFlux2(width=576, height=1024, steps=20, cfg=4.0)
    video = VideoGeneratorComfyUIWan22(width=576, height=1024, length=121, fps=24, steps=20, cfg=5.0)

    shots = [
        {
            "name": "shot_01",
            "image_prompt": f"{STYLE}. Establishing medium-wide shot inside a dim miniature apartment at night. MIA, an adult brunette doll in a burgundy blouse and charcoal trousers, has just opened the front door. EVA, her elegant silver-haired mother doll in a dark teal coat, stands in the hallway holding a tiny red car key at chest height. Both women are visible and frozen in tense eye contact. The red key is clearly readable as the story prop.",
            "motion_prompt": "Locked camera with a very slow push-in. Mia's hand tightens on the door handle. Eva raises the small red car key slightly. Both maintain tense eye contact. Minimal natural doll motion, no speaking, preserve faces, clothing, room and key exactly.",
            "refs": [],
            "seed": 410041,
        },
        {
            "name": "shot_02",
            "image_prompt": f"{STYLE}. Reference identity map: the BRUNETTE woman on the LEFT is MIA and wears burgundy; the SILVER-HAIRED woman on the RIGHT is EVA and wears teal. Do not swap their hair, faces, or clothes. Create a close insert shot from EVA's right-side position: EVA's teal-sleeved hand holds the same tiny red car key in foreground. MIA, still brunette and still wearing burgundy, is softly blurred in the doorway behind it. EVA remains off-camera except for her teal sleeve and hand. Preserve the apartment, lighting, doll scale and prop design. Suspenseful composition.",
            "motion_prompt": "Macro insert, nearly locked camera. Eva slowly rotates the red car key once between her fingers; Mia remains blurred and still behind it. Preserve the exact hand, key, sleeve, lighting and miniature style. No morphing.",
            "refs": ["shot_01"],
            "seed": 410042,
        },
        {
            "name": "shot_03",
            "image_prompt": f"{STYLE}. Using the supplied character and scene references exactly, create a tight reaction close-up of MIA, the same brunette doll in the same burgundy blouse, framed in the doorway. She looks from the red key up toward her mother with restrained shock and dawning betrayal. EVA's teal shoulder and the red key are soft foreground shapes. Keep face, hair, wardrobe, lighting and set continuous.",
            "motion_prompt": "Very slow cinematic push toward Mia. Her eyes shift from the foreground key to Eva, then she makes one tiny backward movement as realization lands. Restrained expression, subtle breathing, preserve the exact doll face, hair, wardrobe and lighting. No dialogue, no morphing.",
            "refs": ["shot_01", "shot_02"],
            "seed": 410043,
        },
    ]

    manifest = {"title": "THE RED KEY", "duration_target": 15.0, "shots": []}
    generated: dict[str, Path] = {}
    for shot in shots:
        refs = [str(generated[name]) for name in shot["refs"]]
        frame_path = OUT / f"{shot['name']}.png"
        if not frame_path.exists():
            result = await image.generate_single_image(shot["image_prompt"], refs, seed=shot["seed"])
            result.save(str(frame_path))
        generated[shot["name"]] = frame_path
        clip_path = OUT / f"{shot['name']}.mp4"
        if not clip_path.exists():
            result = await video.generate_single_video(shot["motion_prompt"], [str(frame_path)], seed=shot["seed"] + 1000)
            result.save(str(clip_path))
        manifest["shots"].append({"name": shot["name"], "frame": frame_path.name, "clip": clip_path.name,
                                  "references": shot["refs"], "seed": shot["seed"]})

    concat = OUT / "concat.txt"
    concat.write_text("".join(f"file '{(OUT / (s['name'] + '.mp4')).as_posix()}'\n" for s in shots), encoding="utf-8")
    final = OUT / "THE_RED_KEY_576x1024.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", str(final),
    ], check=True)
    manifest["final"] = final.name
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(final)


if __name__ == "__main__":
    asyncio.run(main())
