import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";
import { ComfyWidgets } from "/scripts/widgets.js";

const REFRESH_WIDGET_NAME = "dynamicprompts_lite_refresh_wildcards";
const ADVANCED_TOGGLE_WIDGET_NAME = "dynamicprompts_lite_advanced_toggle";
const RANDOM_PROMPT_NODE_TYPES = new Set(["DPRandomGenerator"]);
const RANDOM_PROMPTS_2_ADVANCED_WIDGETS = new Set([
    "seed",
    // ComfyUI automatically adds this companion widget for integer seeds.
    "control_after_generate",
    "autorefresh",
]);
const BUTTON_LABELS = {
    zh: {
        advanced: "高级设置",
        hide: "隐藏",
        refresh: "刷新通配符",
        checking: "检查通配符…",
        unchanged: "未发现改动",
        failed: "刷新失败，请看控制台",
        refreshed: (fileCount) => `已刷新（${fileCount} 个文件）`,
    },
    en: {
        advanced: "Advanced Settings",
        hide: "Hide",
        refresh: "Refresh Wildcards",
        checking: "Checking Wildcards…",
        unchanged: "No changes found",
        failed: "Refresh failed; see console",
        refreshed: (fileCount) => `Refreshed (${fileCount} files)`,
    },
};

function getButtonLabels() {
    // `Comfy.Locale` is the public ComfyUI setting when the legacy settings
    // API is available.  The DOM/browser fallbacks keep older frontends usable.
    const locale = app.ui?.settings?.getSettingValue?.("Comfy.Locale")
        ?? document.documentElement.lang
        ?? navigator.language
        ?? "en";
    return String(locale).toLowerCase().startsWith("zh")
        ? BUTTON_LABELS.zh
        : BUTTON_LABELS.en;
}

function updateButtonLabel(button, label) {
    button.label = label;
    app.graph?.setDirtyCanvas(true, true);
}

function setRandomPrompts2AdvancedVisibility(node, toggleButton, visible) {
    for (const widget of node.widgets ?? []) {
        if (!RANDOM_PROMPTS_2_ADVANCED_WIDGETS.has(widget.name)) {
            continue;
        }

        // `hidden` is required here, not just `advanced`: current Canvas mode
        // reserves layout space for advanced widgets even when it does not draw
        // them.  Hidden widgets are excluded from its size calculation.
        widget.advanced = true;
        widget.hidden = !visible;
    }

    node.showAdvanced = visible;
    toggleButton._dynamicPromptsLiteAdvancedVisible = visible;
    const labels = getButtonLabels();
    toggleButton.label = visible ? labels.hide : labels.advanced;

    // Keep the user's current width (including manual resizing) and change
    // only the height required by the newly visible/hidden widgets.
    const [, height] = node.computeSize();
    node.setSize([node.size[0], height]);
    node.setDirtyCanvas(true, true);
}

async function refreshWildcards(button) {
    const labels = getButtonLabels();
    updateButtonLabel(button, labels.checking);
    try {
        const response = await api.fetchApi(
            "/dynamicprompts-lite/wildcards/refresh",
            { method: "POST" },
        );
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const result = await response.json();
        const label = result.changed
            ? labels.refreshed(result.file_count)
            : labels.unchanged;
        updateButtonLabel(button, label);
    } catch (error) {
        console.error("Dynamic Prompts Lite wildcard refresh failed", error);
        updateButtonLabel(button, labels.failed);
    }

    window.setTimeout(
        () => updateButtonLabel(button, getButtonLabels().refresh),
        2500,
    );
}

app.registerExtension({
    name: "DynamicPromptsLite.RefreshWildcards",

    addCustomNodeDefs() {
        const originalStringWidget = ComfyWidgets.PROMPT;
        if (typeof originalStringWidget === "function") {
            ComfyWidgets.PROMPT = function(node, inputName, inputData, app) {
                const stringWidget = originalStringWidget(node, inputName, inputData, app);
                stringWidget.widget.dynamicPrompts = false;
                return stringWidget;
            };
        }
    },

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (!RANDOM_PROMPT_NODE_TYPES.has(nodeData.name)) {
            return;
        }

        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            const result = originalOnNodeCreated?.apply(this, arguments);

            if (this.widgets?.some((widget) => widget.name === REFRESH_WIDGET_NAME)) {
                return result;
            }

            if (nodeData.name === "DPRandomGenerator") {
                let advancedToggle;
                advancedToggle = this.addWidget(
                    "button",
                    ADVANCED_TOGGLE_WIDGET_NAME,
                    null,
                    () => setRandomPrompts2AdvancedVisibility(
                        this,
                        advancedToggle,
                        !advancedToggle._dynamicPromptsLiteAdvancedVisible,
                    ),
                );
                advancedToggle.serialize = false;
                advancedToggle.label = getButtonLabels().advanced;
                setRandomPrompts2AdvancedVisibility(this, advancedToggle, false);
            }

            const button = this.addWidget(
                "button",
                REFRESH_WIDGET_NAME,
                null,
                () => refreshWildcards(button),
            );
            button.serialize = false;
            button.label = getButtonLabels().refresh;

            if (nodeData.name === "DPRandomGenerator") {
                const [, height] = this.computeSize();
                this.setSize([this.size[0], height]);
                this.setDirtyCanvas(true, true);
            }
            return result;
        };
    },
});
