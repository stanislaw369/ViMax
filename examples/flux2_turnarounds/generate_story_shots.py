import json
import urllib.request
import time
import sys
import os
import copy

SERVER = 'http://127.0.0.1:8188'
WORKFLOW_PATH = r'C:\Users\Shadow\Documents\flux2_klein_gen\flux2_klein_workflow.json'
OUTPUT_DIR = r'C:\Users\Shadow\Documents\flux2_klein_gen'

with open(WORKFLOW_PATH, 'r', encoding='utf-8') as f:
    base_wf = json.load(f)

shots = [
    {
        "prefix": "Flux2-Story-Window",
        "seed": 91827364501,
        "prompt": (
            "The same serious adult female character with dark brown sculpted bob hair and burgundy blouse, "
            "standing by a rainy window at night in a miniature suburban house. Raindrops streaking the glass. "
            "She looks outside into the dark misty street with concern and curiosity. A faint mysterious cyan streetlight glow illuminates her face. "
            "SERIOUS STYLIZED 3D MINIATURE DRAMA aesthetic. Elegant simplified 3D facial geometry, expressive dark eyes, "
            "sculpted hair, realistic adult proportions. Moody cinematic atmosphere, shallow depth of field, handcrafted miniature film set. "
            "High-end stylized 3D animation."
        )
    },
    {
        "prefix": "Flux2-Story-Doorway",
        "seed": 82736451920,
        "prompt": (
            "The same serious adult female character with dark brown sculpted bob hair and charcoal trousers, "
            "walking slowly down the dark hallway of the miniature house toward the front door. "
            "The front door is slightly cracked open, and a striking beam of bright golden and cyan light cuts across the wooden floor and her clothes. "
            "She pauses in suspense and quiet courage. "
            "SERIOUS STYLIZED 3D MINIATURE DRAMA aesthetic. Simplified 3D character geometry, clean shapes, "
            "handcrafted miniature house interior, dramatic chiaroscuro cinematic lighting, adult psychological thriller mood. "
            "High-end stylized 3D animation."
        )
    }
]

for shot in shots:
    wf = copy.deepcopy(base_wf)
    wf["5"]["inputs"]["text"] = shot["prompt"]
    wf["10"]["inputs"]["noise_seed"] = shot["seed"]
    wf["13"]["inputs"]["filename_prefix"] = shot["prefix"]

    payload = json.dumps({"prompt": wf}).encode('utf-8')
    req = urllib.request.Request(
        f"{SERVER}/api/prompt",
        data=payload,
        headers={'Content-Type': 'application/json'}
    )

    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        prompt_id = result.get('prompt_id')
        print(f"Submitted {shot['prefix']}! prompt_id={prompt_id}", flush=True)
    except Exception as e:
        print(f"Error submitting {shot['prefix']}: {e}", flush=True)
        continue

    # Poll history
    start = time.time()
    done = False
    while time.time() - start < 300:
        time.sleep(4)
        try:
            hreq = urllib.request.Request(f"{SERVER}/history/{prompt_id}")
            hresp = urllib.request.urlopen(hreq, timeout=10)
            history = json.loads(hresp.read())
            if prompt_id in history:
                status = history[prompt_id].get('status', {})
                print(f"Job {shot['prefix']} completed! status={status.get('status_str')}", flush=True)
                outputs = history[prompt_id].get('outputs', {})
                for node_id, node_output in outputs.items():
                    if 'images' in node_output:
                        for img in node_output['images']:
                            fname = img['filename']
                            subfolder = img.get('subfolder', '')
                            itype = img.get('type', 'output')
                            url = f"{SERVER}/api/view?filename={fname}&subfolder={subfolder}&type={itype}"
                            print(f"Downloading {fname} from {url}", flush=True)
                            local_dest = os.path.join(OUTPUT_DIR, fname)
                            urllib.request.urlretrieve(url, local_dest)
                            print(f"Saved: {local_dest}", flush=True)
                done = True
                break
        except Exception as err:
            pass
    if not done:
        print(f"Timeout waiting for {shot['prefix']}", flush=True)

print("Batch generation complete!", flush=True)
