"""Internal W10 text-to-image adapter. No game hooks or external process management."""
from dataclasses import dataclass
from http.client import HTTPConnection, HTTPException
from ipaddress import ip_address
import json
from urllib.parse import urlencode, urlsplit
from uuid import UUID, uuid4


WORKFLOW = "anima-txt2img-v2"
ANIMA_CLIP_TYPE = "qwen_image"
LEGACY_WORKFLOW = "anima-txt2img-v1"


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
    model_revision: int = 1


def graph(settings: Settings, positive: str, negative: str, seed: int, *,
          character_model=None, character_loras=(), workflow=WORKFLOW):
    """Build from final prompt text without adding trigger words or changing weights."""
    clip_type = {WORKFLOW: ANIMA_CLIP_TYPE, LEGACY_WORKFLOW: "stable_diffusion"}[workflow]
    nodes = {}

    def add(kind, **inputs):
        key = str(len(nodes) + 1)
        nodes[key] = {"class_type": kind, "inputs": inputs}
        return [key, 0]

    model = add("UNETLoader", unet_name=character_model or settings.model, weight_dtype="default")
    clip = add("CLIPLoader", clip_name=settings.encoder, type=clip_type, device="default")
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


def _listed_options(spec):
    if not isinstance(spec, (list, tuple)) or not spec:
        return None
    options = spec[0]
    if options == "COMBO" and len(spec) > 1 and isinstance(spec[1], dict):
        options = spec[1].get("options")
    return options if isinstance(options, list) else None


class PromptValidationRejected(ValueError):
    """The server explicitly declined this prompt before queuing it."""


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
                message = f"ComfyUI {method} {path.split('?')[0]}: HTTP {res.status}"
                if method == "POST" and path == "/prompt" and res.status == 400:
                    raw = res.read(65537)
                    if len(raw) <= 65536:
                        details = json.loads(raw)
                        error = details.get("error") if isinstance(details, dict) else None
                        if isinstance(error, dict) and error.get("type") == "prompt_outputs_failed_validation":
                            raise PromptValidationRejected(message)
                # A temporary read failure says nothing about the outcome of an accepted prompt.
                if method == "GET" and res.status in (408, 429, 500, 502, 503, 504):
                    raise ConnectionError(message)
                raise ValueError(message)
            if not binary:
                return json.load(res)
            limit = 32 * 1024 * 1024
            data = res.read(limit + 1)
            if len(data) > limit:
                raise ValueError("Generated image exceeds the local size limit")
            return data
        finally:
            conn.close()

    def catalog(self):
        info = self._request("GET", "/object_info")
        if not isinstance(info, dict) or not info:
            raise ValueError("Invalid object_info")
        fields = {"model": ("UNETLoader", "unet_name"), "encoder": ("CLIPLoader", "clip_name"),
                  "vae": ("VAELoader", "vae_name"), "lora": ("LoraLoaderModelOnly", "lora_name"),
                  "sampler": ("KSampler", "sampler_name"), "scheduler": ("KSampler", "scheduler")}
        result = {}
        for name, (kind, key) in fields.items():
            spec = info.get(kind, {}).get("input", {}).get("required", {}).get(key, [])
            result[name] = [v for v in (_listed_options(spec) or []) if isinstance(v, str)]
        required = {"UNETLoader", "CLIPLoader", "VAELoader", "CLIPTextEncode", "EmptyLatentImage",
                    "KSampler", "VAEDecode", "SaveImage"}
        clip = info.get("CLIPLoader", {}).get("input", {})
        types = _listed_options({**clip.get("required", {}), **clip.get("optional", {})}.get("type"))
        return {"choices": result, "missing_nodes": sorted(required - info.keys()),
                "supports_anima_encoder": None if types is None else ANIMA_CLIP_TYPE in types}

    def submit(self, settings, positive, negative, seed, **character):
        nodes, output = graph(settings, positive, negative, seed, **character)
        try:
            info = self._request("GET", "/object_info")
        except (OSError, HTTPException, ValueError) as exc:
            raise ValueError("Could not inspect ComfyUI before submission") from exc
        if not isinstance(info, dict):
            raise ValueError("Invalid ComfyUI node catalog")
        for node in nodes.values():
            kind = node["class_type"]
            definition = info.get(kind)
            spec = definition.get("input") if isinstance(definition, dict) else None
            required = spec.get("required") if isinstance(spec, dict) else None
            optional = spec.get("optional", {}) if isinstance(spec, dict) else None
            if not isinstance(required, dict) or not isinstance(optional, dict):
                raise ValueError(f"Incompatible ComfyUI node: {kind}")
            available = {**required, **optional}
            if required.keys() - node["inputs"].keys() or node["inputs"].keys() - available.keys():
                raise ValueError(f"Incompatible ComfyUI node: {kind}")
            for key, value in node["inputs"].items():
                field = available[key]
                if not isinstance(field, list) or not field or not isinstance(field[0], (str, list)):
                    raise ValueError(f"Invalid ComfyUI input: {kind}.{key}")
                options = _listed_options(field)
                if field[0] == "COMBO" and len(field) > 1 and (
                    not isinstance(field[1], dict) or ("options" in field[1] and options is None)
                ):
                    raise ValueError(f"Invalid ComfyUI input: {kind}.{key}")
                if options is not None and value not in options:
                    raise ValueError(f"Unavailable {kind}.{key}")
        try:
            result = self._request("POST", "/prompt", {"prompt": nodes, "client_id": self.client_id})
            job = str(UUID(result["prompt_id"]))
        except PromptValidationRejected:
            raise
        except (OSError, HTTPException, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ConnectionError("No confirmed prompt ID after submission") from exc
        self._outputs[job] = output
        return job

    def result(self, job):
        """None while pending, image bytes on success; failures never submit another job."""
        image = self.saved_result(job, self._outputs[job])
        if image is not None:
            del self._outputs[job]
        return image

    def saved_result(self, job, output):
        """Read a prompt ID and SaveImage node previously recorded by this game."""
        job = str(UUID(job))
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
        return image
