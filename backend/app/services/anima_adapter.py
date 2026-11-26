"""Internal W10 text-to-image adapter. No game hooks or external process management."""
from dataclasses import dataclass
from http.client import HTTPConnection
from ipaddress import ip_address
import json
from urllib.parse import urlencode, urlsplit
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Settings:
    model: str
    encoder: str
    vae: str
    width: int
    height: int
    steps: int
    cfg: float
    sampler: str
    scheduler: str
    loras: tuple[tuple[str, float], ...] = ()


def graph(settings: Settings, positive: str, negative: str, seed: int, *,
          character_model=None, character_loras=()):
    """Build from final prompt text without adding trigger words or changing weights."""
    nodes = {}

    def add(kind, **inputs):
        key = str(len(nodes) + 1)
        nodes[key] = {"class_type": kind, "inputs": inputs}
        return [key, 0]

    model = add("UNETLoader", unet_name=character_model or settings.model, weight_dtype="default")
    clip = add("CLIPLoader", clip_name=settings.encoder, type="stable_diffusion", device="default")
    vae = add("VAELoader", vae_name=settings.vae)
    for name, strength in (*settings.loras, *character_loras):
        model = add("LoraLoaderModelOnly", model=model, lora_name=name, strength_model=strength)
    samples = add("KSampler", model=model, positive=add("CLIPTextEncode", clip=clip, text=positive),
                  negative=add("CLIPTextEncode", clip=clip, text=negative),
                  latent_image=add("EmptyLatentImage", width=settings.width, height=settings.height, batch_size=1),
                  seed=seed, steps=settings.steps, cfg=settings.cfg, sampler_name=settings.sampler,
                  scheduler=settings.scheduler, denoise=1)
    output = add("SaveImage", images=add("VAEDecode", samples=samples, vae=vae), filename_prefix="nrnf")
    return nodes, output[0]


class Comfy:
    """One manually started loopback server. POST is never retried on unknown outcome."""
    def __init__(self, endpoint, timeout=10):
        addr = urlsplit(endpoint)
        if (addr.scheme != "http" or addr.username is not None or addr.password is not None
                or addr.path not in ("", "/") or addr.query or addr.fragment or not addr.hostname
                or not (addr.hostname == "localhost" or ip_address(addr.hostname).is_loopback)):
            raise ValueError("Expected a local HTTP origin")
        self.host, self.port, self.timeout = addr.hostname, addr.port, timeout
        self.client_id = str(uuid4())
        self._outputs = {}

    def close(self):
        """Forget local job handles without interrupting the external process."""
        self._outputs.clear()

    def _request(self, method, path, body=None, *, binary=False):
        conn = HTTPConnection(self.host, self.port, timeout=self.timeout)
        try:
            data = json.dumps(body, allow_nan=False).encode() if body is not None else None
            conn.request(method, path, data, {"Content-Type": "application/json"} if data else {})
            res = conn.getresponse()
            if res.status != 200:
                raise ValueError(f"ComfyUI {method} {path.split('?')[0]}: HTTP {res.status}")
            return res.read() if binary else json.load(res)
        finally:
            conn.close()

    def submit(self, settings, positive, negative, seed, **character):
        nodes, output = graph(settings, positive, negative, seed, **character)
        info = self._request("GET", "/object_info")
        for node in nodes.values():
            spec = info.get(node["class_type"], {}).get("input", {})
            required = spec.get("required", {})
            available = {**required, **spec.get("optional", {})}
            if (not spec or required.keys() - node["inputs"].keys()
                    or node["inputs"].keys() - available.keys()):
                raise ValueError(f"Incompatible ComfyUI node: {node['class_type']}")
            for key, value in node["inputs"].items():
                allowed = available[key][0]
                if allowed == "COMBO" and len(available[key]) > 1:
                    allowed = available[key][1].get("options")
                if isinstance(allowed, list) and value not in allowed:
                    raise ValueError(f"Unavailable {node['class_type']}.{key}")
        result = self._request("POST", "/prompt", {"prompt": nodes, "client_id": self.client_id})
        job = str(UUID(result["prompt_id"]))
        self._outputs[job] = output
        return job

    def result(self, job):
        """None while pending, image bytes on success; failures never submit another job."""
        output = self._outputs[job]
        entry = self._request("GET", f"/history/{job}").get(job)
        if not entry:
            return None
        status = entry.get("status", {})
        if status.get("status_str") == "error":
            raise ValueError("ComfyUI generation failed")
        if not status.get("completed"):
            return None
        images = entry.get("outputs", {}).get(output, {}).get("images", [])
        if len(images) != 1 or images[0].get("type") != "output":
            raise ValueError("Expected one final image from the submitted SaveImage node")
        item = images[0]
        query = urlencode({key: item[key] for key in ("filename", "subfolder", "type")})
        image = self._request("GET", "/view?" + query, binary=True)
        if not image:
            raise ValueError("ComfyUI returned an empty image")
        del self._outputs[job]
        return image
