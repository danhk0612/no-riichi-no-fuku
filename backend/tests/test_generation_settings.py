from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.services.generation_settings import Config
from app.local_runtime import create_local_runtime
from app.services.anima_adapter import Comfy


class GenerationSettingsTests(TestCase):
    def test_offline_save_conflict_and_restart(self):
        path = "/api/local/generation-settings"
        with TemporaryDirectory() as directory, patch.object(Comfy, "_request", side_effect=AssertionError("unexpected connection")):
            for phase in range(2):
                runtime = create_local_runtime(Path(directory))
                try:
                    with TestClient(runtime.app, headers={"X-Local-Capability":runtime.capability}) as api:
                        data = api.get(path).json()
                        rev = data.pop("revision")
                        if phase == 0:
                            data["common"].update(model="base", loras=[{"name":"shared","strength":0.5}])
                            data["characters"]["1"] = {"model":"", "loras":[{"name":"char","strength":0}]}
                            body = {**data,"expected_revision":rev}
                            self.assertEqual(api.put(path,json=body).status_code,200)
                            self.assertEqual(api.put(path,json=body).status_code,409)
                            self.assertEqual(api.put(path,json={**body,"expected_revision":1,"endpoint":"https://example.org"}).status_code,422)
                        else:
                            self.assertEqual(rev,1)
                            common, char = Config.model_validate(data).inputs_for(1)
                            self.assertEqual((common.model,common.loras,char),("base",(("shared",0.5),),{"character_model":None,"character_loras":(("char",0.0),)}))
                            self.assertEqual(Config.model_validate(data).inputs_for(2)[1]["character_loras"],())
                finally:
                    runtime.close()

    def test_check_reads_only_catalog_and_never_changes_settings(self):
        path = "/api/local/generation-settings"
        with TemporaryDirectory() as directory:
            runtime = create_local_runtime(Path(directory))
            try:
                with TestClient(runtime.app, headers={"X-Local-Capability":runtime.capability}) as api:
                    info={"UNETLoader":{"input":{"required":{"unet_name":[["a","b"]]}}},"KSampler":{"input":{"required":{"sampler_name":["COMBO",{"options":["euler"]}]}}}}
                    with patch.object(Comfy,"_request",return_value=info) as request:
                        data=api.post(path+"/catalog",json={}).json()
                        request.assert_called_once_with("GET","/object_info")
                        self.assertEqual(data["choices"]["model"],["a","b"])
                        self.assertEqual(data["choices"]["sampler"],["euler"])
                        self.assertIn("SaveImage",data["missing_nodes"])
                    with patch.object(Comfy,"_request",side_effect=ConnectionRefusedError):
                        self.assertEqual(api.post(path+"/catalog",json={}).status_code,502)
                    self.assertEqual(api.get(path).json()["revision"],0)
            finally:
                runtime.close()
