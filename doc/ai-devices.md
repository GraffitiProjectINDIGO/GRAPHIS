# AI devices

## Segmentation

Choose the model and processing device in the AI toolbox in the digitizer view.

- **AI off:** nothing is loaded. Changing the model or device only stores the choice.
- **AI on:** the model is loaded and the image is encoded in the background; AI switches on when ready.
  Changing the model or device while AI is on loads the new model in the background.
- **New image while AI is on:** AI stays on. The model stays loaded; only the new image is encoded.
- **AI switched off:** masks, pre-classification and prompts are removed from the image, and the model is
  released from memory (including GPU memory). Switching AI on again loads the model again.

AI masks are drawn directly above the image and below all region geometries; prompt markers stay on top.

| Device | Windows | Linux | macOS |
|---|---|---|---|
| CPU | yes | yes | yes |
| NVIDIA GPU | CUDA build of PyTorch | CUDA build of PyTorch | - |
| AMD GPU | DirectML (experimental, opt-in) | ROCm build of PyTorch | - |
| Apple GPU | - | - | MPS |

- **Auto** uses CUDA/ROCm, then the Apple GPU, otherwise CPU. It never selects DirectML.
- **CPU fallback:** if a GPU cannot be initialised or an operation fails on it, GRAPHIS switches to CPU once,
  retaining the image and prompts. The info log reports the fallback and the active device.
- **ROCm** builds of PyTorch use PyTorch's CUDA interface, so AMD GPUs on Linux appear as "AMD ROCm".
  Install PyTorch from the ROCm wheel index for your ROCm version.
- **DirectML** is only offered when `torch-directml` is installed (`pip install -e ".[ai,directml]"`).
  It constrains the PyTorch version and Microsoft no longer develops it further. SAM3 uses complex tensors that
  DirectML cannot handle, so DirectML is hidden for SAM3.

The device list is detected the first time AI is used. PyTorch is imported on the GUI thread at that point,
because importing it first in a worker thread crashes model construction on Windows.

GPU acceleration is not necessarily faster than CPU, particularly with a small integrated GPU. On CPU,
MobileSAM encodes an image in well under a second, SAM2 in a few seconds and SAM3 in 15-20 seconds.

MobileSAM and SAM2 can be downloaded with the **Download...** button in the segmentation row of the AI
configuration; SAM3 and TextureSAM are downloaded manually (see README, AI models). When a download puts the models
into a new folder and the selected model is not there, the toolbox switches to the downloaded model. At startup,
the toolbox selects the first model found in the segmentation folder. PyInstaller does not install GPU drivers.

## Speech recognition

Speech uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper) on CPU (CTranslate2, int8) on all
platforms; it needs neither PyTorch nor a GPU. Install it with `pip install -e ".[speech]"`.

- The model is loaded once in a background thread when the speech window opens and stays loaded.
- **Live** mode shows the sentence being spoken in grey and adds it to the text when you pause.
  Without Live mode, the recording is transcribed when it stops.
- **Language:** choose a language code or Auto. Auto detects the language from the first sentence and keeps it
  for the rest of the recording.
- **Models:** `base` is fast; `small` is more accurate and still real-time on most CPUs. Models are only
  downloaded on request, with the **Download...** button in the speech window or AI configuration. Each model is
  saved in its own subfolder of the chosen folder, which becomes the speech model folder. Each subfolder containing
  `model.bin` appears in the model list. OpenAI Whisper `.pt` files are not supported.

## Model folders

The **AI configuration** button in the top toolbar selects one folder for segmentation models and one for speech
models. The settings are stored in `ai_models.json` in the GRAPHIS configuration folder. No models are bundled
with the executable, and GRAPHIS searches no other locations: without a configured folder, no models are found.
