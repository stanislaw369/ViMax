# Local ComfyUI backend: Flux.2 + Wan 2.2

This fork adds ViMax-compatible local renderers:

- `tools.ImageGeneratorComfyUIFlux2` — Flux.2 Klein text-to-image and multi-reference editing.
- `tools.VideoGeneratorComfyUIWan22` — Wan 2.2 TI2V 5B first-frame animation.

The ready configuration is `configs/script2video_comfyui.yaml`. ComfyUI is expected at
`http://127.0.0.1:8188`. Run the controlled vertical smoke test from the repository root:

```powershell
.\.venv\Scripts\python.exe -m examples.toy_microdrama_comfyui_demo
```

The demo is resumable: existing frames and clips are reused. Outputs are written to
`.working_dir/toy_microdrama_comfyui_demo`.

## Recommended production workflow

Do not treat a previous full shot as the only reference. It preserves overall palette but can
swap identities, duplicate props, or lock the next shot to the old composition.

For each episode, prepare and approve these assets before animation:

1. One neutral identity sheet per character (front, 3/4, profile, full body, fixed wardrobe).
2. One clean location plate per camera axis.
3. One clean prop sheet for plot-critical objects.
4. One explicit composition guide per shot (crop, sketch, depth layers, or masked source frame).
5. A first frame and optional end frame approved at still-image resolution.

The shot manifest should map references by role (`character`, `location`, `prop`, `composition`),
not pass an unordered list. Inserts and reaction close-ups should use a crop/mask workflow so the
model changes framing without repainting every identity. Only approved first frames go to Wan.

For iteration, render Wan at 81 frames (3.375 s at 24 fps). Use 121 frames only after still-frame
approval. Keep motion prompts to one character action plus one camera action.
