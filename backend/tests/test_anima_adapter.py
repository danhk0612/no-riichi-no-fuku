from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from unittest import TestCase
from uuid import uuid4
import json

from app.services.anima_adapter import Comfy, Settings, graph


class AnimaAdapterTest(TestCase):
    settings = Settings("base", "encoder", "vae", 512, 768, 20, 4, "sampler", "scheduler", (("shared", 0.7),))

    def test_character_chain_and_raw_prompt(self):
        nodes, out = graph(self.settings, " p\n", " n", 73, character_model="other", character_loras=[("actor", 0.0)])
        def source(link): return nodes[link[0]]["inputs"]
        sampler = source(source(nodes[out]["inputs"]["images"])["samples"])
        actor = source(sampler["model"])
        common = source(actor["model"])
        self.assertEqual((actor["lora_name"], actor["strength_model"], common["lora_name"]), ("actor", 0, "shared"))
        self.assertEqual(source(common["model"])["unet_name"], "other")
        self.assertEqual((source(sampler["positive"])["text"], source(sampler["negative"])["text"], sampler["seed"]), (" p\n", " n", 73))

    def test_local_server_pending_and_owned_output(self):
        nodes, output = graph(self.settings, "", "", 1)
        spec = {n["class_type"]: {"input": {"required": {k: ["*"] for k in n["inputs"]}}} for n in nodes.values()}
        job, seen = str(uuid4()), []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                seen.append(self.path)
                json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                self.send_response(200); self.end_headers(); self.wfile.write(json.dumps({"prompt_id": job}).encode())
            def do_GET(self):
                seen.append(self.path)
                self.send_response(200); self.end_headers()
                if self.path.startswith("/view?"):
                    self.wfile.write(b"owned"); return
                data = spec if self.path == "/object_info" else {}
                if self.path.startswith("/history/") and seen.count(self.path) == 2:
                    data = {job: {"status": {"completed": True}, "outputs": {
                        "preview": {"images": [{"filename": "wrong"}]}, output: {"images": [
                            {"type": "output", "filename": "only.png", "subfolder": ""}]}}}}
                self.wfile.write(json.dumps(data).encode())
        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            t = Thread(target=server.serve_forever); t.start()
            try:
                client = Comfy(f"http://127.0.0.1:{server.server_port}")
                with self.assertRaises(KeyError): client.result(str(uuid4()))
                self.assertEqual(client.submit(self.settings, "", "", 1), job)
                self.assertIsNone(client.result(job))
                self.assertEqual(client.result(job), b"owned")
                self.assertIn("filename=only.png", seen[-1])
                del spec["KSampler"]
                with self.assertRaisesRegex(ValueError, "KSampler"): client.submit(self.settings, "", "", 1)
                self.assertEqual(seen.count("/prompt"), 1)
            finally:
                server.shutdown(); t.join()
