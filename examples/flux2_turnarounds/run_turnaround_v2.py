import json
import urllib.request
import time
import sys
import os
import copy

SERVER = 'http://127.0.0.1:8188'
OUTPUT_DIR = r'C:\Users\Shadow\Documents\flux2_klein_gen'

with open(os.path.join(OUTPUT_DIR, 'turnaround_base_v2.json')) as f:
    base_workflow = json.load(f)

views = [
    {
        "name": "Front",
        "seed": 2918473625,
        "prompt": "Full body turnaround reference sheet of the same serious adult female character from the reference image, now standing in a front-facing view on a plain pure white background. She faces the camera directly, standing straight with arms relaxed at her sides, holding a smartphone loosely in one hand. She wears the same dark burgundy blouse and charcoal trousers. SERIOUS STYLIZED 3D MINIATURE DRAMA aesthetic: elegant simplified 3D facial geometry, moderately enlarged expressive eyes, sculpted dark brown hair, simplified hands, realistic adult proportions, mature and serious expression. Clean studio lighting, soft even illumination, no harsh shadows, full body visible from head to plain shoes. High-end stylized 3D animation character. Not photorealistic, not cute, not anime, not cartoon.",
        "prefix": "Flux2-Turnaround-Front-v2"
    },
    {
        "name": "ThreeQuarterFront",
        "seed": 5829103471,
        "prompt": "Full body turnaround reference sheet of the same serious adult female character from the reference image, now standing in a three-quarter front view on a plain pure white background. Her body is turned approximately 45 degrees to the left, face visible at a three-quarter angle showing both eyes. She stands straight with arms relaxed, holding a smartphone loosely in one hand. She wears the same dark burgundy blouse and charcoal trousers. SERIOUS STYLIZED 3D MINIATURE DRAMA aesthetic: elegant simplified 3D facial geometry, moderately enlarged expressive eyes, sculpted dark brown hair, simplified hands, realistic adult proportions, mature and serious expression. Clean studio lighting, soft even illumination, full body visible from head to plain shoes. High-end stylized 3D animation character. Not photorealistic, not cute, not anime, not cartoon.",
        "prefix": "Flux2-Turnaround-ThreeQuarterFront-v2"
    },
    {
        "name": "SideProfile",
        "seed": 7382910463,
        "prompt": "Full body turnaround reference sheet of the same serious adult female character from the reference image, now standing in a exact side profile view on a plain pure white background. Her body faces exactly 90 degrees to the right, only her left profile is visible: nose, chin, jawline, and the side of her hair. She stands straight with arms relaxed, holding a smartphone loosely in one hand. She wears the same dark burgundy blouse and charcoal trousers. SERIOUS STYLIZED 3D MINIATURE DRAMA aesthetic: elegant simplified 3D facial geometry, moderately enlarged expressive eyes, sculpted dark brown hair, simplified hands, realistic adult proportions, mature and serious expression. Clean studio lighting, soft even illumination, full body visible from head to plain shoes. High-end stylized 3D animation character. Not photorealistic, not cute, not anime, not cartoon.",
        "prefix": "Flux2-Turnaround-SideProfile-v2"
    },
    {
        "name": "ThreeQuarterBack",
        "seed": 1928374650,
        "prompt": "Full body turnaround reference sheet of the same serious adult female character from the reference image, now standing in a three-quarter back view on a plain pure white background. Her body is turned approximately 135 degrees, showing mostly her back and shoulder area with a small sliver of her face visible on one side. She stands straight with arms relaxed, holding a smartphone loosely in one hand. The back of her sculpted dark brown hair is clearly visible. She wears the same dark burgundy blouse and charcoal trousers. SERIOUS STYLIZED 3D MINIATURE DRAMA aesthetic: simplified 3D character proportions, sculpted hair shapes, simplified hands, realistic adult proportions. Clean studio lighting, soft even illumination, full body visible from head to plain shoes. High-end stylized 3D animation character. Not photorealistic, not cute, not anime, not cartoon.",
        "prefix": "Flux2-Turnaround-ThreeQuarterBack-v2"
    },
    {
        "name": "Back",
        "seed": 4738291056,
        "prompt": "Full body turnaround reference sheet of the same serious adult female character from the reference image, now standing in a full back view on a plain pure white background. Her entire back faces the camera: the back of her head, her hair, shoulders, back of her burgundy blouse, and the back of her charcoal trousers. No face is visible. She stands straight with arms relaxed, holding a smartphone loosely in one hand. The back of her sculpted dark brown hair is the main focal point. SERIOUS STYLIZED 3D MINIATURE DRAMA aesthetic: simplified 3D character proportions, sculpted hair shapes from behind, simplified hands, realistic adult proportions. Clean studio lighting, soft even illumination, full body visible from head to plain shoes. High-end stylized 3D animation character. Not photorealistic, not cute, not anime, not cartoon.",
        "prefix": "Flux2-Turnaround-Back-v2"
    }
]

results = []

for view in views:
    wf = copy.deepcopy(base_workflow)
    wf["10"]["inputs"]["text"] = view["prompt"]
    wf["12"]["inputs"]["noise_seed"] = view["seed"]
    wf["15"]["inputs"]["filename_prefix"] = view["prefix"]

    payload = json.dumps({"prompt": wf}).encode('utf-8')
    req = urllib.request.Request(
        SERVER + '/api/prompt',
        data=payload,
        headers={'Content-Type': 'application/json'}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        prompt_id = result.get('prompt_id')
        print(f'Submitted {view["name"]}: prompt_id={prompt_id}')
        results.append({"view": view["name"], "prompt_id": prompt_id, "prefix": view["prefix"]})
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f'HTTP Error for {view["name"]}: {error_body}')
    time.sleep(2)

print(f'\nAll {len(results)} views submitted. Polling...')

completed = set()
max_wait = 900
start = time.time()

while len(completed) < len(results) and time.time() - start < max_wait:
    time.sleep(8)
    elapsed = int(time.time() - start)

    for r in results:
        if r["view"] in completed:
            continue
        pid = r["prompt_id"]
        try:
            hreq = urllib.request.Request(f'{SERVER}/history/{pid}')
            hresp = urllib.request.urlopen(hreq, timeout=10)
            history = json.loads(hresp.read())
            if pid in history:
                status = history[pid].get('status', {})
                status_str = status.get('status_str', 'unknown')
                print(f'  [{elapsed}s] {r["view"]}: {status_str}')

                if status_str == 'success':
                    outputs = history[pid].get('outputs', {})
                    for node_id, node_output in outputs.items():
                        if 'images' in node_output:
                            for img in node_output['images']:
                                filename = img['filename']
                                subfolder = img.get('subfolder', '')
                                img_type = img.get('type', 'output')
                                params = f'filename={filename}&subfolder={subfolder}&type={img_type}'
                                url = f'{SERVER}/api/view?{params}'
                                ireq = urllib.request.Request(url)
                                iresp = urllib.request.urlopen(ireq, timeout=30)
                                img_data = iresp.read()
                                out_path = os.path.join(OUTPUT_DIR, filename)
                                with open(out_path, 'wb') as f:
                                    f.write(img_data)
                                print(f'    Downloaded: {out_path} ({len(img_data)} bytes)')
                    completed.add(r["view"])
                elif status_str == 'error':
                    print(f'    ERROR: {json.dumps(status)}')
                    completed.add(r["view"])
        except Exception as e:
            pass

    try:
        qreq = urllib.request.Request(SERVER + '/queue')
        qresp = urllib.request.urlopen(qreq, timeout=10)
        queue = json.loads(qresp.read())
        running = len(queue.get('queue_running', []))
        pending = len(queue.get('queue_pending', []))
        print(f'  [{elapsed}s] Queue: {running} running, {pending} pending, {len(completed)}/{len(results)} done')
    except:
        pass

print(f'\nCompleted: {len(completed)}/{len(results)}')
for r in results:
    status = 'OK' if r['view'] in completed else 'MISSING'
    print(f'  {r["view"]}: {status}')
