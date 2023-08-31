const POLLING_TIMEOUT = 500;

function uuidv4() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c => (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16));
}

const WEBUI_CLIENT_ID = uuidv4();

function changeDisplayedWorkflowType(targetWorkflowType) {
    const targetIFrameElement = getWorkflowTypeIFrame(targetWorkflowType);
    const currentIFrameElement = targetIFrameElement.parentElement.querySelector(".comfyui-workflow-type-visible");
    currentIFrameElement.classList.remove("comfyui-workflow-type-visible");
    targetIFrameElement.classList.add("comfyui-workflow-type-visible");
}

document.addEventListener("DOMContentLoaded", () => {
    onComfyuiTabLoaded(clearEnabledDisplayNames);
    onComfyuiTabLoaded(setupComfyuiTabEvents);
});

function onComfyuiTabLoaded(callback) {
    if (getClearEnabledDisplayNamesButtons().some(e => e === null) ||
        getWorkflowTypeIds() === null ||
        getComfyuiContainer() === null ||
        getTabNav() === null
    ) {
        // webui not yet ready, try again in a bit
        setTimeout(() => { onComfyuiTabLoaded(callback); }, POLLING_TIMEOUT);
        return;
    }

    callback();
}

function clearEnabledDisplayNames() {
    for (const clearButton of getClearEnabledDisplayNamesButtons()) {
        clearButton.click();
    }
}

function setupComfyuiTabEvents() {
    setupResizeTabEvent();
    setupToggleFooterEvent();

    updateComfyuiTabHeight();

    getWorkflowTypeIds().forEach(id => setupIFrame(id));
}

function reloadComfyuiIFrames() {
    getWorkflowTypeIds().forEach(id => {
        const comfyuiFrame = getWorkflowTypeIFrame(id);
        reloadFrameElement(comfyuiFrame);
    });
}

function setupResizeTabEvent() {
    window.addEventListener("resize", updateComfyuiTabHeight);
}

function setupToggleFooterEvent() {
    new MutationObserver((mutationsList) => {
        for (const mutation of mutationsList) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                updateFooterStyle();
            }
        }
    })
    .observe(getComfyuiTab(), { attributes: true });
}

function updateComfyuiTabHeight() {
    const container = getComfyuiContainer();
    const tabNavBottom = getTabNav().getBoundingClientRect().bottom;
    container.style.height = `calc(100% - ${tabNavBottom}px)`;
}

function updateFooterStyle() {
    const tabDisplay = getComfyuiTab().style.display;
    const footer = getFooter();

    if(footer === null) return;
    if(tabDisplay === 'block') {
        footer.classList.add('comfyui-remove-display');
    }
    else {
        footer.classList.remove('comfyui-remove-display');
    }
}

function getClearEnabledDisplayNamesButtons() {
    return [
        document.getElementById("script_txt2txt_comfyui_clear_enabled_display_names") ?? document.getElementById("script_txt2img_comfyui_clear_enabled_display_names") ?? null,
        document.getElementById("script_img2img_comfyui_clear_enabled_display_names") ?? null,
    ];
}

function getTabNav() {
    const tabs = document.getElementById("tabs") ?? null;
    return tabs ? tabs.querySelector(".tab-nav") : null;
}

function getComfyuiTab() {
    return document.getElementById("tab_comfyui_webui_root") ?? null;
}

function getComfyuiContainer() {
    return document.getElementById("comfyui_webui_container") ?? null;
}

function getFooter() {
    return document.querySelector('#footer') ?? null;
}

function getWorkflowTypeIFrame(workflowTypeId) {
    return document.querySelector(`[workflow_type_id="${workflowTypeId}"]`);
}

function getWorkflowTypeIds() {
    return getExtensionDynamicProperty('workflow_type_ids');
}

function getExtensionDynamicProperty(key) {
    return JSON.parse(document.querySelector(`[sd_webui_comfyui_key="${key}"]`)?.innerText ?? "null");
}

function reloadFrameElement(iframeElement) {
    iframeElement.src += "";
}

function setupIFrame(workflowTypeId) {
    let messageToReceive = workflowTypeId;

    const iframeSearchParams = new URLSearchParams();
    iframeSearchParams.set("workflowTypeId", workflowTypeId);
    iframeSearchParams.set("webuiClientId", WEBUI_CLIENT_ID);
    const iframe = getWorkflowTypeIFrame(workflowTypeId);
    const base_src = iframe.getAttribute("base_src");
    iframe.src = base_src + "?" + iframeSearchParams.toString();
}
