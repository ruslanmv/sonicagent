## Model registry

Neural model binaries are not stored in Git. The registry contains metadata, paths, checksums, licenses, and attribution.

Default voice mirror base:

```text
https://huggingface.co/ruslanmv/hp-piper-voices/resolve/main
```

Example model path pattern:

```text
{lang}/{locale}/{speaker}/{quality}/{voice_id}.onnx
{lang}/{locale}/{speaker}/{quality}/{voice_id}.onnx.json
```

Download scripts are placeholders until model hashes and redistribution review are finalized:

```bash
python scripts/download_voice.py --voice it_IT-paola-medium
python scripts/download_stt_model.py --model small
python scripts/verify_model_checksums.py
```

The model cache defaults to `~/.cache/SonicAgent` and should be mounted as a persistent volume in deployments.

