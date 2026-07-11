import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";
import { ComfyWidgets } from "/scripts/widgets.js";

const REFRESH_BUTTON = "刷新 Wildcards";
const IDLE_LABEL = REFRESH_BUTTON;

function updateButtonLabel(button, label) {
    button.label = label;
    app.graph?.setDirtyCanvas(true, true);
}

async function refreshWildcards(button) {
    updateButtonLabel(button, "检查 Wildcards…");
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
            ? `已刷新（${result.file_count} 个文件）`
            : "未发现改动";
        updateButtonLabel(button, label);
    } catch (error) {
        console.error("Dynamic Prompts Lite wildcard refresh failed", error);
        updateButtonLabel(button, "刷新失败，请看控制台");
    }

    window.setTimeout(() => updateButtonLabel(button, IDLE_LABEL), 2500);
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
        if (nodeData.name !== "DPRandomGenerator") {
            return;
        }

        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            const result = originalOnNodeCreated?.apply(this, arguments);
            if (this.widgets?.some((widget) => widget.name === REFRESH_BUTTON)) {
                return result;
            }

            const button = this.addWidget(
                "button",
                REFRESH_BUTTON,
                null,
                () => refreshWildcards(button),
            );
            button.serialize = false;
            return result;
        };
    },
});
