# Voice catalog

This is the voice library SonicAgent can run. Every row is a selectable id in `model_registry/voices.json`. The audio files are the Piper voices in [`ruslanmv/hp-piper-voices`](https://huggingface.co/ruslanmv/hp-piper-voices). The voice image downloads every unique file at build time. The files are not stored in Git.

`GET /v1/voices` returns this same library. `installed` is true only when that ONNX file and its config are on the machine answering the request.

## What the two styles are for

One server covers two jobs.

- **Companion** is the warmer, slower, softer preset. It is the delivery for an adult companion or a fan-service line.
- **Secretary** is the clearer, slightly faster preset. It is the delivery for work.

Where the mirror has one female speaker, Companion and Secretary share her file and differ only by the settings below. Male speakers and unlabeled speakers stay in the catalog under their published names. They are not companion or secretary presets.

No voice in this mirror was trained to sound explicit, breathy, or seductive. The companion preset does not become that kind of model. A voice with that purpose would be a new file, with its own license and checksum, published on the mirror and pinned here. That file is not available to download today.

## Style settings

These are Piper synthesis controls. `length_scale` above 1 is slower. Lower noise is steadier.

| Style | length_scale | noise_scale | noise_w_scale | Use |
| --- | ---: | ---: | ---: | --- |
| companion | 1.16 | 0.8 | 0.92 | Adult companion and fan-service line |
| secretary | 0.94 | 0.48 | 0.6 | Work |
| catalog | 1.0 | 0.667 | 0.8 | Published speaker, unchanged |

## What is already included

- **49 selectable voices.**
- **44 ONNX files.** The voice image installs all of them from the mirror. Companion and Secretary ids that share a speaker do not download a second file.
- **Languages:** English (US), English (UK), Spanish (Spain), Spanish (Mexico), French, German, Italian, Portuguese.
- **License:** MIT, from the Piper voice projects mirrored in `ruslanmv/hp-piper-voices`.
- Portuguese in this mirror is Edresson and Faber. Both are male. There is no female Portuguese voice to assign to Companion or Secretary.

## Voices

### English (US)

| Id | Name | Role | Gender | Quality | Fit | Upgrade |
| --- | --- | --- | --- | --- | --- | --- |
| `en_US-kristin-medium` | Kristin | companion | female | medium | Adult companion. Warmer and slower. | No higher quality of this speaker is in the mirror. |
| `en_US-lessac-medium` | Lessac | secretary | female | medium | Work. Clearer and a little faster. | No higher quality of this speaker is in the mirror. |
| `en_US-amy-low` | Amy | catalog | female | low | Published female speaker. Neutral settings. | Same speaker also has medium. |
| `en_US-amy-medium` | Amy | catalog | female | medium | Published female speaker. Neutral settings. | Same speaker also has low. |
| `en_US-arctic-medium` | Arctic | catalog | unspecified | medium | Speaker is not labeled. Not assigned a gendered role. | No higher quality of this speaker is in the mirror. |
| `en_US-bryce-medium` | Bryce | catalog | male | medium | Published male speaker. | No higher quality of this speaker is in the mirror. |
| `en_US-danny-low` | Danny | catalog | male | low | Published male speaker. | No higher quality of this speaker is in the mirror. |
| `en_US-hfc_female-medium` | HFC Female | catalog | female | medium | Published female speaker. Neutral settings. | No higher quality of this speaker is in the mirror. |
| `en_US-hfc_male-medium` | HFC Male | catalog | male | medium | Published male speaker. | No higher quality of this speaker is in the mirror. |
| `en_US-joe-medium` | Joe | catalog | male | medium | Published male speaker. | No higher quality of this speaker is in the mirror. |
| `en_US-john-medium` | John | catalog | male | medium | Published male speaker. | No higher quality of this speaker is in the mirror. |
| `en_US-kathleen-low` | Kathleen | catalog | female | low | Published female speaker. Neutral settings. | No higher quality of this speaker is in the mirror. |
| `en_US-libritts_r-medium` | LibriTTS | catalog | unspecified | medium | Speaker is not labeled. Not assigned a gendered role. | No higher quality of this speaker is in the mirror. |
| `en_US-norman-medium` | Norman | catalog | male | medium | Published male speaker. | No higher quality of this speaker is in the mirror. |
| `en_US-ryan-low` | Ryan | catalog | male | low | Published male speaker. | Same speaker also has medium. |
| `en_US-ryan-medium` | Ryan | catalog | male | medium | Published male speaker. | Same speaker also has low. |

### English (UK)

| Id | Name | Role | Gender | Quality | Fit | Upgrade |
| --- | --- | --- | --- | --- | --- | --- |
| `en_GB-cori-medium` | Cori | companion | female | medium | Adult companion. Warmer and slower. | No higher quality of this speaker is in the mirror. |
| `en_GB-alba-medium` | Alba | secretary | female | medium | Work. Clearer and a little faster. | No higher quality of this speaker is in the mirror. |
| `en_GB-alan-medium` | Alan | catalog | male | medium | Published male speaker. | No higher quality of this speaker is in the mirror. |
| `en_GB-aru-medium` | Aru | catalog | unspecified | medium | Speaker is not labeled. Not assigned a gendered role. | No higher quality of this speaker is in the mirror. |
| `en_GB-jenny_dioco-medium` | Jenny | catalog | female | medium | Published female speaker. Neutral settings. | No higher quality of this speaker is in the mirror. |
| `en_GB-northern_english_male-medium` | Northern English | catalog | male | medium | Published male speaker. | No higher quality of this speaker is in the mirror. |
| `en_GB-southern_english_female-low` | Southern English | catalog | female | low | Published female speaker. Neutral settings. | No higher quality of this speaker is in the mirror. |

### Español (España)

| Id | Name | Role | Gender | Quality | Fit | Upgrade |
| --- | --- | --- | --- | --- | --- | --- |
| `es_ES-sharvard-companion` | Sharvard, speaker 1 | companion | female | medium | Adult companion. Warmer and slower. | No higher quality of this speaker is in the mirror. Same file as es_ES-sharvard-secretary, es_ES-sharvard-male. |
| `es_ES-sharvard-secretary` | Sharvard, speaker 1 | secretary | female | medium | Work. Clearer and a little faster. | No higher quality of this speaker is in the mirror. Same file as es_ES-sharvard-companion, es_ES-sharvard-male. |
| `es_ES-sharvard-male` | Sharvard, speaker 0 | catalog | male | medium | Published male speaker. | No higher quality of this speaker is in the mirror. Same file as es_ES-sharvard-companion, es_ES-sharvard-secretary. |
| `es_ES-carlfm-x_low` | Carlfm | catalog | male | x_low | Published male speaker. | No higher quality of this speaker is in the mirror. |
| `es_ES-davefx-medium` | DaveFX | catalog | male | medium | Published male speaker. | No higher quality of this speaker is in the mirror. |

### Español (México)

| Id | Name | Role | Gender | Quality | Fit | Upgrade |
| --- | --- | --- | --- | --- | --- | --- |
| `es_MX-ald-companion` | Ald | companion | female | medium | Adult companion. Warmer and slower. | No higher quality of this speaker is in the mirror. Same file as es_MX-ald-medium. |
| `es_MX-ald-medium` | Ald | secretary | female | medium | Work. Clearer and a little faster. | No higher quality of this speaker is in the mirror. Same file as es_MX-ald-companion. |
| `es_MX-claude-high` | Claude | catalog | male | high | Published male speaker. | Highest quality published for this speaker. |

### Français

| Id | Name | Role | Gender | Quality | Fit | Upgrade |
| --- | --- | --- | --- | --- | --- | --- |
| `fr_FR-upmc-medium` | Jessica, speaker 0 | companion | female | medium | Adult companion. Warmer and slower. | No higher quality of this speaker is in the mirror. Same file as fr_FR-upmc-pierre. |
| `fr_FR-siwis-medium` | Siwis | secretary | female | medium | Work. Clearer and a little faster. | Same speaker also has low. |
| `fr_FR-gilles-low` | Gilles | catalog | male | low | Published male speaker. | No higher quality of this speaker is in the mirror. |
| `fr_FR-siwis-low` | Siwis | catalog | female | low | Published female speaker. Neutral settings. | Same speaker also has medium. |
| `fr_FR-tom-medium` | Tom | catalog | male | medium | Published male speaker. | No higher quality of this speaker is in the mirror. |
| `fr_FR-upmc-pierre` | Pierre, speaker 1 | catalog | male | medium | Published male speaker. | No higher quality of this speaker is in the mirror. Same file as fr_FR-upmc-medium. |

### Deutsch

| Id | Name | Role | Gender | Quality | Fit | Upgrade |
| --- | --- | --- | --- | --- | --- | --- |
| `de_DE-eva_k-x_low` | Eva K | companion | female | x_low | Adult companion. Warmer and slower. | No higher quality of this speaker is in the mirror. |
| `de_DE-kerstin-low` | Kerstin | secretary | female | low | Work. Clearer and a little faster. | No higher quality of this speaker is in the mirror. |
| `de_DE-karlsson-low` | Karlsson | catalog | male | low | Published male speaker. | No higher quality of this speaker is in the mirror. |
| `de_DE-mls-medium` | Mls | catalog | unspecified | medium | Speaker is not labeled. Not assigned a gendered role. | No higher quality of this speaker is in the mirror. |
| `de_DE-pavoque-low` | Pavoque | catalog | male | low | Published male speaker. | No higher quality of this speaker is in the mirror. |
| `de_DE-thorsten-medium` | Thorsten | catalog | male | medium | Published male speaker. | No higher quality of this speaker is in the mirror. |
| `de_DE-thorsten_emotional-medium` | Thorsten Emotional | catalog | unspecified | medium | Speaker is not labeled. Not assigned a gendered role. | No higher quality of this speaker is in the mirror. |

### Italiano

| Id | Name | Role | Gender | Quality | Fit | Upgrade |
| --- | --- | --- | --- | --- | --- | --- |
| `it_IT-paola-companion` | Paola | companion | female | medium | Adult companion. Warmer and slower. | No higher quality of this speaker is in the mirror. Same file as it_IT-paola-medium. |
| `it_IT-paola-medium` | Paola | secretary | female | medium | Work. Clearer and a little faster. | No higher quality of this speaker is in the mirror. Same file as it_IT-paola-companion. |
| `it_IT-riccardo-x_low` | Riccardo | catalog | male | x_low | Published male speaker. | No higher quality of this speaker is in the mirror. |

### Português

| Id | Name | Role | Gender | Quality | Fit | Upgrade |
| --- | --- | --- | --- | --- | --- | --- |
| `pt_BR-edresson-low` | Edresson | catalog | male | low | Published male speaker. | No higher quality of this speaker is in the mirror. |
| `pt_BR-faber-medium` | Faber | catalog | male | medium | Published male speaker. | No higher quality of this speaker is in the mirror. |

## How to upgrade later

1. Prefer a higher Piper quality when the mirror publishes one for the same speaker. Amy, Ryan, and Siwis already have a lower file and a medium file. Use medium unless you need the smaller file. Claude, `es_MX-claude-high`, is the only `high` file in this mirror.
2. Add a new speaker by putting the ONNX and config on `ruslanmv/hp-piper-voices`, pinning both sha256 values in `model_registry/voices.json`, and rebuilding the voice image. The image downloads the new file. Do not commit the ONNX into this repository.
3. A dedicated explicit or seductive model is a step 2 addition. It is not hidden in the current 44 files.
4. Do not relabel an unlabeled multi-speaker model, such as LibriTTS, Arctic, or MLS, as a female companion. The speaker gender is not identified on those files.

## Checked against the mirror

The 44 ONNX paths in `voices.json` are the 44 `.onnx` files in `ruslanmv/hp-piper-voices` at the time of this catalog. Four files are selected by more than one id:

- `es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx`: `es_ES-sharvard-companion`, `es_ES-sharvard-secretary`, `es_ES-sharvard-male`
- `es/es_MX/ald/medium/es_MX-ald-medium.onnx`: `es_MX-ald-companion`, `es_MX-ald-medium`
- `fr/fr_FR/upmc/medium/fr_FR-upmc-medium.onnx`: `fr_FR-upmc-medium`, `fr_FR-upmc-pierre`
- `it/it_IT/paola/medium/it_IT-paola-medium.onnx`: `it_IT-paola-companion`, `it_IT-paola-medium`

