import json
import struct
from io import BytesIO
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from app.local_runtime import create_local_runtime
from app.services.anima_adapter import Comfy, Settings, graph
from app.services.hand_cg_cache import HandCG

def chunk(kind, body):
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
PNG = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB",1,1,8,0,0,0,0)) + chunk(b"IDAT",zlib.compress(b"\x00\x00")) + chunk(b"IEND",b"")
FROZEN = {"workflow":"anima-txt2img-v1","stage":1,"kind":"hand_cg","positive":"p","negative":"n",
          "settings":{"model":"m","encoder":"c","vae":"v","width":512,"height":512,"steps":10,"cfg":4,"sampler":"euler","scheduler":"normal"}}


class HandCacheTests(TestCase):
    def test_unknown_restart_concurrent_retry_and_missing_file(self):
        with TemporaryDirectory() as tmp:
            def service(): return HandCG(Path(tmp))
            endpoint="http://127.0.0.1:8188"
            with patch.object(Comfy,"submit",side_effect=TimeoutError) as submit:
                first=service().advance(FROZEN,endpoint)
                self.assertEqual(first["state"],"uncertain")
                original_seed=submit.call_args.args[-1]
                self.assertEqual(service().advance(FROZEN,endpoint),first)
                self.assertEqual(submit.call_count,1)
            with patch.object(Comfy,"submit",return_value=str(uuid4())) as submit, patch.object(Comfy,"saved_result",return_value=PNG):
                with ThreadPoolExecutor(max_workers=4) as pool:
                    list(pool.map(lambda _:service().advance(FROZEN,endpoint,first["attempt"]),range(4)))
                ready=service().advance(FROZEN,endpoint)
                self.assertEqual(ready["state"],"ready")
                self.assertEqual(submit.call_count,1)
                self.assertEqual(submit.call_args.args[-1],original_seed)
                self.assertEqual(service().image(FROZEN,ready["attempt"]),PNG)
                self.assertNotEqual(service().directory(FROZEN),service().directory({**FROZEN,"settings":{**FROZEN["settings"],"model_revision":2}}))
                next(Path(tmp).rglob("*.png")).unlink()
                missing=service().advance(FROZEN,endpoint)
                self.assertEqual(missing["state"],"missing")
                service().advance(FROZEN,endpoint)
                self.assertEqual(submit.call_count,1)
                self.assertEqual(service().advance(FROZEN,endpoint,missing["attempt"])["state"],"pending")

    def test_workflow_revision_does_not_reuse_or_replace_old_image(self):
        with TemporaryDirectory() as tmp, patch.object(Comfy, "submit", return_value=str(uuid4())) as submit, patch.object(Comfy, "saved_result", return_value=PNG):
            cache = HandCG(Path(tmp))
            endpoint = "http://127.0.0.1:8188"
            for workflow in ("anima-txt2img-v1", "anima-txt2img-v2"):
                frozen = {**FROZEN, "workflow": workflow}
                self.assertEqual(cache.advance(frozen, endpoint)["state"], "pending")
                self.assertEqual(submit.call_args.kwargs["workflow"], workflow)
                self.assertEqual(cache.advance(frozen, endpoint)["state"], "ready")
            self.assertEqual(cache.advance(FROZEN, endpoint)["state"], "ready")
            self.assertEqual(submit.call_count, 2)

    def test_known_job_survives_disconnect_without_resubmission(self):
        with TemporaryDirectory() as tmp, patch.object(Comfy,"submit",return_value=str(uuid4())) as submit, patch.object(Comfy,"saved_result",side_effect=[TimeoutError,None,PNG]) as poll:
            cache=HandCG(Path(tmp))
            def advance(retry=None):return cache.advance(FROZEN,"http://127.0.0.1:8188",retry)
            self.assertEqual(advance()["state"],"pending")
            failed=advance()
            self.assertEqual(failed["state"],"disconnected")
            self.assertEqual(advance(),failed)
            self.assertEqual(advance(failed["attempt"])["state"],"pending")
            self.assertEqual(advance()["state"],"ready")
            self.assertEqual(submit.call_count,1)
            self.assertEqual(len(set(tuple(x.args) for x in poll.call_args_list)),1)

    def test_invalid_preflight_never_submits_and_retries_only_after_input(self):
        nodes, _ = graph(Settings(**FROZEN["settings"]), "p", "n", 1, workflow=FROZEN["workflow"])
        valid = {n["class_type"]: {"input":{"required":{k:["*"] for k in n["inputs"]}}} for n in nodes.values()}
        bad_fields = [{**valid, "UNETLoader": {"input": {"required": {"unet_name": field, "weight_dtype": ["*"]}}}}
                      for field in ([], ["COMBO", {"options": "invalid"}])]
        for bad in ([], {"UNETLoader": None}, {"UNETLoader": {"input": {"required": []}}}, *bad_fields):
            with self.subTest(bad=bad), TemporaryDirectory() as tmp, patch.object(Comfy, "_request") as request:
                endpoint = "http://127.0.0.1:8188"
                cache = HandCG(Path(tmp))
                request.side_effect = [bad, valid, {"prompt_id": str(uuid4())}]
                failed = cache.advance(FROZEN, endpoint)
                self.assertEqual(failed["state"], "failed")
                self.assertEqual(HandCG(Path(tmp)).advance(FROZEN, endpoint), failed)
                request.assert_called_once_with("GET", "/object_info")
                self.assertEqual(cache.advance(FROZEN, endpoint, failed["attempt"])["state"], "pending")
                self.assertEqual([c.args[:2] for c in request.call_args_list],
                                 [("GET", "/object_info"), ("GET", "/object_info"), ("POST", "/prompt")])

    def test_prompt_validation_rejection_is_distinct_from_lost_receipt(self):
        nodes, _ = graph(Settings(**FROZEN["settings"]), "p", "n", 1, workflow=FROZEN["workflow"])
        info = {n["class_type"]: {"input": {"required": {k: ["*"] for k in n["inputs"]}}}
                for n in nodes.values()}

        def response(status, body):
            reply = BytesIO(body)
            reply.status = status
            return reply

        rejection = json.dumps({"error":{"type":"prompt_outputs_failed_validation"},
                                "node_errors":{}}).encode()
        for code, body, expected in ((400, rejection, "rejected"), (400, b"bad response", "uncertain"),
                                     (503, rejection, "uncertain"), (200, b"{}", "uncertain")):
            with self.subTest(code=code, body=body), TemporaryDirectory() as tmp, patch("app.services.anima_adapter.HTTPConnection") as connect:
                conn = connect.return_value
                conn.getresponse.side_effect = [response(200, json.dumps(info).encode()), response(code, body)]
                cache = HandCG(Path(tmp))
                first = cache.advance(FROZEN, "http://127.0.0.1:8188")
                self.assertEqual(first["state"], expected)
                self.assertEqual(cache.advance(FROZEN, "http://127.0.0.1:8188"), first)
                self.assertEqual([c.args[:2] for c in conn.request.call_args_list],
                                 [("GET", "/object_info"), ("POST", "/prompt")])

    def test_transient_history_and_image_http_errors_keep_the_original_job(self):
        job = str(uuid4())
        endpoint = "http://127.0.0.1:8188"
        _, output = graph(Settings(**FROZEN["settings"]), "p", "n", 1, workflow=FROZEN["workflow"])
        history = json.dumps({job: {"status": {"completed": True}, "outputs": {output: {"images": [
            {"type": "output", "filename": "owned.png", "subfolder": ""}]}}}}).encode()

        def reply(status, data=b""):
            response = BytesIO(data)
            response.status = status
            return response

        with TemporaryDirectory() as tmp, patch.object(Comfy, "submit", return_value=job) as submit, patch("app.services.anima_adapter.HTTPConnection") as connection:
            conn = connection.return_value
            conn.getresponse.side_effect = [reply(503), reply(200, history), reply(429), reply(200, history), reply(200, PNG)]
            def advance(retry=None):
                return HandCG(Path(tmp)).advance(FROZEN, endpoint, retry)
            attempt = advance()["attempt"]
            self.assertEqual(advance(), {"state": "disconnected", "attempt": attempt})
            self.assertEqual(advance()["state"], "disconnected")
            self.assertEqual(conn.request.call_count, 1)
            self.assertEqual(advance(attempt), {"state": "disconnected", "attempt": attempt})
            self.assertEqual(advance(attempt), {"state": "ready", "attempt": attempt})
            self.assertEqual(HandCG(Path(tmp)).image(FROZEN, attempt), PNG)
            submit.assert_called_once()
            self.assertEqual([call.args[:2] for call in conn.request.call_args_list],
                             [("GET", f"/history/{job}"), ("GET", f"/history/{job}"),
                              ("GET", "/view?filename=owned.png&subfolder=&type=output"),
                              ("GET", f"/history/{job}"), ("GET", "/view?filename=owned.png&subfolder=&type=output")])

    def test_api_cold_resume_and_old_event_rejection(self):
        from test_result_delivery import ResultDeliveryTests
        with TemporaryDirectory() as tmp, patch.object(Comfy,"submit",return_value=str(uuid4())) as submit, patch.object(Comfy,"saved_result",return_value=PNG):
            runtime=create_local_runtime(Path(tmp))
            try:
                with TestClient(runtime.app,headers={"X-Local-Capability":runtime.capability}) as client:
                    self.assertEqual(client.put("/api/local/generation-settings",json={"expected_revision":0,"common":{"model":"m","vae":"v","encoder":"c"}}).status_code,200)
                    generation=ResultDeliveryTests()._build_completed(runtime,content=True,hand_defaults=True)
                    base="/api/local/play/sessions/c1-test-session/results"
                    params={"generation":generation}
                    envelope=client.get(base,params=params).json()
                    self.assertEqual(envelope["head"]["payload"]["content"]["scene"]["generation_input"]["workflow"], "anima-txt2img-v2")
                    event=envelope["head"]["event_id"]
                    route=f"{base}/{event}/cg"
                    self.assertEqual(client.post(route,params=params).json()["state"],"pending")
            finally: runtime.close()
            runtime=create_local_runtime(Path(tmp))
            try:
                with TestClient(runtime.app,headers={"X-Local-Capability":runtime.capability}) as client:
                    ready=client.post(route,params=params).json()
                    self.assertEqual(ready["state"],"ready")
                    image=f"{route}/{ready['attempt']}"
                    self.assertEqual(client.get(image,params=params).content,PNG)
                    ack=client.post(base+"/ack",json={**params,"event_id":event,"ordinal":envelope["head"]["ordinal"],"expected_delivery_revision":envelope["delivery_revision"]})
                    self.assertEqual(ack.status_code,200,ack.text)
                    self.assertEqual(client.get(image,params=params).status_code,409)
                    self.assertEqual(client.post(route,params=params).status_code,409)
                    self.assertEqual(submit.call_count,1)
            finally: runtime.close()

    def test_saved_hand_prompt_changes_only_on_regenerate(self):
        from test_result_delivery import ResultDeliveryTests
        with TemporaryDirectory() as tmp, patch.object(Comfy, "submit", return_value=str(uuid4())) as submit, patch.object(Comfy, "saved_result", return_value=PNG):
            runtime = create_local_runtime(Path(tmp))
            try:
                with TestClient(runtime.app, headers={"X-Local-Capability":runtime.capability}) as api:
                    api.put("/api/local/generation-settings", json={"expected_revision":0,
                            "common":{"model":"m","vae":"v","encoder":"c"}}).raise_for_status()
                    generation = ResultDeliveryTests()._build_completed(runtime, content=True, hand_defaults=True)
                    base = "/api/local/play/sessions/c1-test-session/results"
                    params = {"generation":generation}
                    event = api.get(base, params=params).json()["head"]["event_id"]
                    path = f"{base}/{event}/cg"
                    api.post(path, params=params).raise_for_status()
                    original = api.post(path, params=params).json()
                    previous = api.get(path+"/prompt", params=params).json()["positive"]
                    api.put(path+"/prompt", params=params, json={"previous":previous,"positive":"edited scene"}).raise_for_status()
                    self.assertEqual(api.post(path, params=params).json(), original)
                    api.post(path, params={**params,"regenerate":"true"}).raise_for_status()
                    replacement = api.post(path, params=params).json()
                    self.assertEqual(replacement["state"], "ready")
                    self.assertNotEqual(original["attempt"], replacement["attempt"])
                    self.assertEqual(submit.call_count, 2)
                    self.assertEqual(submit.call_args.args[1], "edited scene")
            finally:
                runtime.close()

    def test_ack_does_not_wait_for_generator(self):
        from threading import Event
        from test_result_delivery import ResultDeliveryTests
        began, release = Event(), Event()
        def delayed(*args, **kwargs):
            began.set()
            if not release.wait(8):
                raise TimeoutError
            return str(uuid4())
        with TemporaryDirectory() as tmp, patch.object(Comfy, "submit", side_effect=delayed):
            runtime = create_local_runtime(Path(tmp))
            try:
                with TestClient(runtime.app, headers={"X-Local-Capability":runtime.capability}) as client:
                    client.put("/api/local/generation-settings",json={"expected_revision":0,"common":{"model":"m","vae":"v","encoder":"c"}}).raise_for_status()
                    generation = ResultDeliveryTests()._build_completed(runtime,content=True,hand_defaults=True)
                    base = "/api/local/play/sessions/c1-test-session/results"
                    params = {"generation":generation}
                    envelope = client.get(base,params=params).json()
                    head = envelope["head"]
                    route = f"{base}/{head['event_id']}/cg"
                    with ThreadPoolExecutor(max_workers=1) as pool:
                        future = pool.submit(client.post,route,params=params)
                        try:
                            self.assertTrue(began.wait(3))
                            ack = client.post(base+"/ack",json={**params,"event_id":head["event_id"],"ordinal":head["ordinal"],"expected_delivery_revision":envelope["delivery_revision"]})
                            self.assertEqual(ack.status_code,200,ack.text)
                            self.assertEqual(ack.json()["head"]["kind"],"settlement")
                        finally:
                            release.set()
                        self.assertEqual(future.result().json()["state"],"pending")
                    self.assertEqual(client.post(route,params=params).status_code,409)
            finally:
                runtime.close()
