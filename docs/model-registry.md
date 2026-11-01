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

Install the pinned Whisper Tiny checkpoint and every voice in the registry with:

```bash
python hf/scripts/setup-models.py --model tiny --tts --cache-dir ~/.cache/sonicagent-rt
```

Whisper Tiny has a pinned revision and `model.bin` checksum. Each Piper voice in `voices.json` has `model_sha256` from the mirror's Git LFS oid and `config_sha256` from the config file bytes. The model cache should be a persistent volume in any deployment.

