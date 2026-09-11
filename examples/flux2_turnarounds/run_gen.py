import json
import urllib.request
import time
import sys
import os

WORKFLOW_PATH = r'C:\Users\Shadow\Documents\flux2_klein_gen\flux2_klein_workflow.json'
OUTPUT_DIR = r'C:\Users\Shadow\Documents\flux2_klein_gen'
SERVER = 'http://127.0.0.1:8188'

with open(WORKFLOW_PATH) as f:
    workflow = json.load(f)

payload = json.dumps({"prompt": workflow}).encode('utf-8')
req = urllib.request.Request(
    SERVER + '/api/prompt',
    data=payload,
    headers={'Content-Type': 'application/json'}
)

try:
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read())
    prompt_id = result.get('prompt_id')
    print(f"Submitted! prompt_id={prompt_id}")
except urllib.error.HTTPError as e:
    error_body = e.read().decode('utf-8')
    print(f"HTTP Error {e.code}: {error_body}")
    sys.exit(1)

max_wait = 600
start = time.time()
while time.time() - start < max_wait:
    time.sleep(5)
    elapsed = int(time.time() - start)

    try:
        hreq = urllib.request.Request(f'{SERVER}/history/{prompt_id}')
        hresp = urllib.request.urlopen(hreq, timeout=10)
        history = json.loads(hresp.read())

        if prompt_id in history:
            status = history[prompt_id].get('status', {})
            status_str = status.get('status_str', 'unknown')
            print(f"\nJob finished! status={status_str}")

            outputs = history[prompt_id].get('outputs', {})

            for node_id, node_output in outputs.items():
                if 'images' in node_output:
                    for img in node_output['images']:
                        filename = img['filename']
                        subfolder = img.get('subfolder', '')
                        img_type = img.get('type', 'output')

                        params = f'filename={filename}&subfolder={subfolder}&type={img_type}'
                        url = f'{SERVER}/api/view?{params}'
                        print(f"Downloading: {url}")
                        ireq = urllib.request.Request(url)
                        iresp = urllib.request.urlopen(ireq, timeout=30)
                        img_data = iresp.read()

                        out_path = os.path.join(OUTPUT_DIR, filename)
                        with open(out_path, 'wb') as f:
                            f.write(img_data)
                        print(f"Saved to: {out_path} ({len(img_data)} bytes)")
            break
    except Exception as e:
        print(f"Poll error: {e}")

    try:
        qreq = urllib.request.Request(SERVER + '/queue')
        qresp = urllib.request.urlopen(qreq, timeout=10)
        queue = json.loads(qresp.read())
        running = len(queue.get('queue_running', []))
        pending = len(queue.get('queue_pending', []))
        print(f"[{elapsed}s] Running: {running}, Pending: {pending}")
    except:
        pass
else:
    print(f"Timed out after {max_wait}s")
