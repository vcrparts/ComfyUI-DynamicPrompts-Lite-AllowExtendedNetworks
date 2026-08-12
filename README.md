FORK CHANGES : VIBECODED WARNING!!! I will not be maintaining or updating this, just for personal use. Updated sampler.py and wildcard refresh.py. Random prompt node now wont refresh every time respecting fixed seed, saving time. Wildcards location follows extra_model_paths.yaml, no more mklink or moving your wildcards all over the place.

# ComfyUI DynamicPrompts Lite

Maintained fork of [adieyal/comfyui-dynamicprompts](https://github.com/adieyal/comfyui-dynamicprompts), focused on fast startup, current ComfyUI compatibility, and practical wildcard workflows.

## What changed

- `Magic Prompt` was removed. It depended on Transformers and a local Hugging Face model, but is not needed by this Lite fork.
- The remaining nodes no longer import Magic Prompt dependencies during ComfyUI startup.
- `Random Prompts` has a `刷新 Wildcards` button. Save wildcard-file changes, click the button, then run your workflow without restarting ComfyUI.
- Repeated refresh clicks without changed `.txt`, `.json`, or `.yaml` wildcard files retain the current cache.

## Included nodes

1. `Random Prompts` - random variants and wildcard sampling.
2. `Combinatorial Prompts` - cycles through combinations of variants and wildcards.
3. `I'm Feeling Lucky` - obtains a related prompt through Lexica when used.
4. `Jinja2 Templates` - prompt templates using Jinja2.
5. `OutputString` - displays a string in the ComfyUI output panel.

## Installation

Clone this fork into ComfyUI's `custom_nodes` directory:

```powershell
git clone https://github.com/ZiYao00/ComfyUI-DynamicPrompts-Lite.git custom_nodes/ComfyUI-DynamicPrompts-Lite
python -m pip install -r custom_nodes/ComfyUI-DynamicPrompts-Lite/requirements.txt
```

Restart ComfyUI once after installation. No separate `install.py` step is needed.

## Wildcards

The plugin uses its own `wildcards` directory. It supports `.txt`, `.json`, and `.yaml` wildcard files. A Windows directory Junction is supported, which is useful when one wildcard library is shared by multiple ComfyUI installations:

```bat
mklink /J "custom_nodes\ComfyUI-DynamicPrompts-Lite\wildcards" "G:\CommonFile\wildcards\wildcards"
```

After editing and saving any supported wildcard file:

1. Click `刷新 Wildcards` on a `Random Prompts` node.
2. Run the workflow normally.

The button checks file names, modification times, and sizes. It only invalidates Lite's cached wildcard data when a change is detected. It does not refresh other custom nodes' wildcard caches.

## Compatibility notes

- Existing workflows containing `DPMagicPrompt` will show a missing node because Magic Prompt was intentionally removed.
- This fork keeps the other original node identifiers for workflow compatibility.
- The shared wildcard directory itself is ignored by Git and is never included in this repository.

## Credits and license

This fork retains the original project's [MIT License](LICENSE) and attribution. Dynamic prompt syntax and wildcard behavior are provided by the [dynamicprompts](https://github.com/adieyal/dynamicprompts) Python library.

See [the changelog](docs/CHANGELOG.md) for release notes.
