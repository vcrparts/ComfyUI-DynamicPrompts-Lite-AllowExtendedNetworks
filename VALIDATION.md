# Validation record

## Batch 1 - Lazy-load MagicPrompt dependencies

### Goal

Prevent the optional MagicPrompt feature from importing Transformers, Torch, and
their related dependencies while ComfyUI is only discovering node definitions.

### Change

- `nodes/magicprompt.py`
  - Moved `RandomPromptGenerator` and `MagicPromptGenerator` imports from module
    scope into `_ensure_prompt_generator()`.
  - Create those generators only when a non-empty MagicPrompt request is run.
  - Kept the existing node id (`DPMagicPrompt`), category, input schema, and
    output type unchanged.

### Measurements

| Check | Original | Lazy-load version |
| --- | ---: | ---: |
| Isolated `import nodes` | 29.36 s | 0.20 s |
| Test-package custom-node import | 44.9 s | 0.1 s |
| `GET /object_info/DPMagicPrompt` | not measured | 323.6 ms |

### Verified

- Python syntax compilation passed.
- All six original node registrations remain present.
- The test ComfyUI server started normally.
- `DPMagicPrompt` remains available through the server node-definition API with
  category `Dynamic Prompts` and `STRING` output.
- The new startup log contains no TensorFlow import message caused by this plugin.

### Deliberately not exercised

Executing a non-empty MagicPrompt request loads the Hugging Face model
`Gustavosta/MagicPrompt-Stable-Diffusion`; when it is not already cached, that
can download model data. This was not triggered during the startup-performance
batch. It must be tested separately before publishing the change.

### Scope and rollback

- Development repository: `G:\GitHub\ComfyUI-DynamicPrompts-Lite`
- Test deployment: only
  `G:\AIGC\ComfyUI_test\ComfyUI\custom_nodes\comfyui-dynamicprompts\nodes\magicprompt.py`
- Main package: untouched.
- Rollback is a one-file restore from the original repository version; no files
  or directories were removed or moved.

## Batch 2 - Remove the Magic Prompt node from the plugin interface

### Goal

The maintained Lite version does not need local model-based prompt expansion.
The user uses an online API for that purpose.

### Change

- Removed `DPMagicPrompt` from `nodes/__init__.py` imports, node mappings, and
  display-name mappings.
- Kept `nodes/magicprompt.py` as an unused source file. Keeping it has no
  startup cost because it is no longer imported, and makes a future restore
  straightforward.

### Expected result

- The ComfyUI node menu and `/object_info` no longer expose `DPMagicPrompt`.
- The plugin cannot load or download the MagicPrompt Hugging Face model.
- Existing workflows that contain `DPMagicPrompt` will show that node as
  missing; this is intentional for this Lite version.

### Verified

- The test ComfyUI server restarted successfully.
- DynamicPrompts still imports in 0.1 seconds.
- `GET /object_info/DPMagicPrompt` returns `{}`, while a retained node returns
  its complete definition.
- The retained development registration list is:
  `DPRandomGenerator`, `DPCombinatorialGenerator`, `DPFeelingLucky`, `DPJinja`,
  and `DPOutput`.

## Batch 3 - Make the development repository the test-package source of truth

### Goal

Use `G:\GitHub\ComfyUI-DynamicPrompts-Lite` as the only editable plugin source.
The test package must load that source directly, while preserving the original
plugin intact outside `custom_nodes`.

### Change

- Updated `nodes/sampler.py` to locate `wildcards` relative to the plugin's own
  source directory instead of the hard-coded `comfyui-dynamicprompts` folder.
- Added `/wildcards/` to `.gitignore`; the local wildcard directory is a
  Junction and must never be committed.
- Created the development wildcard Junction:
  `G:\GitHub\ComfyUI-DynamicPrompts-Lite\wildcards` ->
  `G:\CommonFile\wildcards\wildcards`.
- Restored the two files previously changed in the test package's original
  plugin, then moved that complete original plugin to:
  `G:\AIGC\ComfyUI_test\ComfyUI\custom_nodes.backup\comfyui-dynamicprompts-original`.
- Created the test-package Junction:
  `G:\AIGC\ComfyUI_test\ComfyUI\custom_nodes\ComfyUI-DynamicPrompts-Lite` ->
  `G:\GitHub\ComfyUI-DynamicPrompts-Lite`.

### Verified

- The test-package startup log explicitly loaded
  `custom_nodes\ComfyUI-DynamicPrompts-Lite` in 0.1 seconds.
- The test server started and listened on port 8190.
- The retained random-prompt node has a complete server definition.
- `DPMagicPrompt` returns an empty definition and is not registered.
- The runtime wildcard lookup resolves to
  `G:\GitHub\ComfyUI-DynamicPrompts-Lite\wildcards`.
- The original plugin was moved intact rather than deleted; its original
  wildcard Junction was retained in the backup.

## Batch 4 - Manual wildcard refresh from Random Prompts

### Goal

Allow a user to save wildcard-file changes and refresh Dynamic Prompts Lite
without restarting ComfyUI. Repeated refresh clicks with no wildcard changes
must not discard the current cache.

### Change

- Added `nodes/wildcard_refresh.py`.
  - Builds a lightweight manifest from supported wildcard files (`.txt`,
    `.json`, `.yaml`) using relative path, modification time, and size.
  - Changes the refresh revision only when that manifest changes.
- Updated sampler-based nodes to clear the existing wildcard manager and prompt
  iterator only after the refresh revision changes.
- Added `POST /dynamicprompts-lite/wildcards/refresh`.
- Added `WEB_DIRECTORY = "./web"` and the modern frontend script `web/dp.js`.
  It adds a non-serialized `刷新 Wildcards` button to `Random Prompts` only.
- Preserved the old `web-extensions/dp.js` file as historical source; it is not
  deleted or loaded by the Lite frontend.

### Verified

- A compressed pre-change source backup was created at:
  `G:\AIGC\ComfyUI_test\ComfyUI\custom_nodes.backup\ComfyUI-DynamicPrompts-Lite_before_wildcard_refresh_20260711_002140.zip`.
  It excludes `.git`, `__pycache__`, and the wildcard Junction data.
- Python compilation and JavaScript syntax checks passed.
- Isolated checks showed the first refresh changes state and an immediate second
  refresh without file edits reports no change.
- The test ComfyUI server loaded `ComfyUI-DynamicPrompts-Lite` in 0.1 seconds.
- The live refresh endpoint returned:
  - first request: `changed=true`, `revision=1`, `file_count=741`;
  - second request: `changed=false`, `revision=1`, `file_count=741`.
- The frontend script is available at
  `/extensions/ComfyUI-DynamicPrompts-Lite/dp.js` and contains the refresh
  button implementation.

### Remaining visual check

The local Chrome session was blocked from opening `127.0.0.1:8190` by the
current browser access policy. Therefore the button's visual placement was not
clicked through Chrome in this batch. The server route and script delivery were
verified directly.

## Batch 5 - Release preparation

### Change

- Renamed the distribution to `comfyui-dynamicprompts-lite` and set the Lite
  release version to `0.3.0`.
- Replaced the Magic Prompt dependency extra with the retained Feeling Lucky
  dependency extra. Transformers is no longer declared as an installation
  dependency.
- Rewrote the README for this maintained fork, including installation,
  wildcard Junction, manual refresh, compatibility, attribution, and license
  information.
- Updated the legacy `install.py` so it no longer copies files into ComfyUI's
  installation directory; `WEB_DIRECTORY` now provides the frontend directly.
- Added the release notes to `docs/CHANGELOG.md`.

### Verified

- Python, JavaScript, and TOML parsing checks passed.
- The published dependency declaration is
  `dynamicprompts[feelinglucky]~=0.30.2`.
- A final test-package startup imported Lite in 0.2 seconds and reached
  `Starting server` without a Lite traceback.

### Test-environment note

The final test process subsequently stopped listening on port 8190 before the
post-restart endpoint check. The prior Batch 4 runtime endpoint checks remain
valid because the refresh implementation was unchanged in this batch. No Lite
exception was recorded in the startup log.
