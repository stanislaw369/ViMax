import json
import urllib.request
import time
import os
import copy

SERVER = 'http://127.0.0.1:8188'
WORKFLOW_PATH = r'C:\Users\Shadow\Documents\flux2_klein_gen\flux2_klein_workflow.json'
OUTPUT_DIR = r'C:\Users\Shadow\Documents\flux2_klein_gen'

with open(WORKFLOW_PATH, 'r', encoding='utf-8') as f:
    base_wf = json.load(f)

shot = {
    "prefix": "Flux2-Story-PhoneMacro",
    "seed": 73619284055,
    "prompt": (
        "Extreme close-up macro shot of a sleek smartphone held in a female hand with tidy nails. "
        "The screen of the smartphone is lit up brightly in the dark living room, displaying a mysterious high-tech encrypted message interface: "
        "'ALERT: 23:42 - SPOJRZ W OKNO'. Cyan and amber neon glow from the screen reflecting on the fingers and glass. "
        "SERIOUS STYLIZED 3D MINIATURE DRAMA aesthetic. Clean stylized 3D geometry, high detail glass reflection, "
        "dramatic moody lighting, shallow depth of field, handcrafted miniature house set. "
        "High-end stylized 3D animation."
    )
}

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

resp = urllib.request.urlopen(req, timeout=30)
result = json.loads(resp.read())
prompt_id = result.get('prompt_id')
print(f"Submitted {shot['prefix']}! prompt_id={prompt_id}", flush=True)

start = time.time()
while time.time() - start < 300:
    time.sleep(4)
    try:
        hreq = urllib.request.Request(f"{SERVER}/history/{prompt_id}")
        hresp = urllib.request.urlopen(hreq, timeout=10)
        history = json.loads(hresp.read())
        if prompt_id in history:
            print("Completed generation!", flush=True)
            outputs = history[prompt_id].get('outputs', {})
            for node_id, node_output in outputs.items():
                if 'images' in node_output:
                    for img in node_output['images']:
                        fname = img['filename']
                        subfolder = img.get('subfolder', '')
                        itype = img.get('type', 'output')
                        url = f"{SERVER}/api/view?filename={fname}&subfolder={subfolder}&type={itype}"
                        dest = os.path.join(OUTPUT_DIR, fname)
                        urllib.request.urlretrieve(url, dest)
                        print(f"Downloaded local image: {dest}", flush=True)
            break
    except Exception as e:
        print("Polling...", flush=True)
