"""Bundle detectors. Both return a boolean 'fabric' mask for the line band.

ClassicalDetector - zero dependencies, CPU, runs anywhere (incl. a phone via
                    OpenCV). Fabric = coloured pixels that are NOT part of the
                    static scene (bins, shirts, machines).
SamDetector       - SAM 3 text-prompted ("stack of cut garment pieces"),
                    zero-shot, runs locally on a free Colab GPU. Optional.
"""
from __future__ import annotations
import cv2
import numpy as np


class ClassicalDetector:
    name = "classical"

    def __init__(self, sat_min=45, val_min=110, static_freq=0.8, grey_max=150):
        self.sat_min, self.val_min, self.static_freq = sat_min, val_min, static_freq
        self.grey_max = grey_max
        self.static = None

    def _coloured(self, band):
        hsv = cv2.cvtColor(band, cv2.COLOR_BGR2HSV)
        coloured = (hsv[..., 1] > self.sat_min) & (hsv[..., 2] > self.val_min)
        # grey / dark fabric: clearly darker than white table & light-grey floor
        grey = (hsv[..., 1] <= self.sat_min) & (hsv[..., 2] < self.grey_max) & (hsv[..., 2] > 70)
        return coloured | grey

    def fit(self, band_frames):
        """Learn which coloured pixels never change (static scene)."""
        acc = np.zeros(band_frames[0].shape[:2], np.float32)
        for f in band_frames:
            acc += self._coloured(f)
        self.static = (acc / len(band_frames)) > self.static_freq

    def fabric_mask(self, band):
        m = self._coloured(band)
        if self.static is not None:
            m &= ~self.static
        return m


class SamDetector:
    """SAM 3 zero-shot bundle segmentation via Hugging Face transformers.

    Needs: pip install transformers torch ; an accepted licence on the model
    page and `huggingface-cli login` (free). Checkpoint id is configurable
    because the SAM 3.x checkpoint name depends on what Meta has published.
    """
    name = "sam3"

    def __init__(self, model_id="facebook/sam3", prompt="stack of cut garment fabric pieces",
                 threshold=0.4, device=None):
        import torch
        from transformers import Sam3Model, Sam3Processor
        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = Sam3Processor.from_pretrained(model_id)
        self.model = Sam3Model.from_pretrained(model_id).to(self.device).eval()
        self.prompt, self.threshold = prompt, threshold
        self.static = None

    def fit(self, band_frames):
        pass  # zero-shot: nothing to learn, no dataset, no labels

    def fabric_mask(self, band):
        from PIL import Image
        img = Image.fromarray(cv2.cvtColor(band, cv2.COLOR_BGR2RGB))
        inputs = self.processor(images=img, text=self.prompt, return_tensors="pt").to(self.device)
        with self.torch.no_grad():
            out = self.model(**inputs)
        original_sizes = inputs.get("original_sizes")
        target_sizes = original_sizes.tolist() if original_sizes is not None else [img.size[::-1]]
        res = self.processor.post_process_instance_segmentation(
            out, threshold=self.threshold, mask_threshold=0.5,
            target_sizes=target_sizes)[0]
        masks = res["masks"]
        if len(masks) == 0:
            return np.zeros(band.shape[:2], bool)
        return masks.cpu().numpy().any(axis=0)


def make_detector(kind="classical", **kw):
    if kind == "sam3":
        return SamDetector(**kw)
    return ClassicalDetector()
