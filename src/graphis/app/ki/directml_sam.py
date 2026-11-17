"""Adapt Ultralytics' CUDA/CPU setup to a real DirectML torch.device."""

from graphis.app.ki.devices import torch_directml_device


def adapt_prompt_encoders(model, device):
    import torch
    from torch.utils._pytree import tree_map

    class CPUPromptEncoder(torch.nn.Module):
        def __init__(self, encoder):
            super().__init__()
            self.encoder = encoder.cpu()

        def forward(self, *args, **kwargs):
            # DirectML cannot concatenate the zero-length sparse tensor used by
            # SAM prompt encoders. This small stage runs on CPU; the expensive
            # image encoder and mask decoder remain on the GPU.
            def to_cpu(value):
                return value.cpu() if isinstance(value, torch.Tensor) else value
            result = self.encoder(*tree_map(to_cpu, args), **tree_map(to_cpu, kwargs))
            return tree_map(lambda value: value.to(device) if isinstance(value, torch.Tensor) else value, result)

        def get_dense_pe(self):
            return self.encoder.get_dense_pe().to(device)

        def __getattr__(self, name):
            try:
                return super().__getattr__(name)
            except AttributeError:
                return getattr(super().__getattr__("encoder"), name)

    for name in ("prompt_encoder", "sam_prompt_encoder"):
        encoder = getattr(model, name, None)
        if encoder is not None:
            setattr(model, name, CPUPromptEncoder(encoder))


def directml_predictor_class(base_class):
    class DirectMLPredictor(base_class):
        def set_image(self, image):
            import torch

            with torch.inference_mode(False), torch.no_grad():
                return super().set_image(image)

        def stream_inference(self, *args, **kwargs):
            import torch

            # DirectML's repeat_interleave requires tensor version counters,
            # which inference_mode disables. Use no_grad for this predictor only.
            inference = getattr(base_class.stream_inference, "__wrapped__", None)
            if inference is None:
                raise RuntimeError("This Ultralytics version cannot run DirectML without inference_mode.")
            with torch.inference_mode(False), torch.no_grad():
                yield from inference(self, *args, **kwargs)

        def setup_model(self, model=None, verbose=True):
            # Leave args.device="cpu" for Ultralytics' device validation. All
            # tensor creation and inference then use self.device below.
            super().setup_model(model, verbose=False)
            device = torch_directml_device()
            # Rebuild eval-time caches on the GPU (notably TinyViT attention).
            self.model = self.model.train().float().to(device).eval()
            adapt_prompt_encoders(self.model, device)
            self.device = device
            self.mean = self.mean.to(device)
            self.std = self.std.to(device)
            self.model.fp16 = False

    return DirectMLPredictor
