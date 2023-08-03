const POLLING_TIMEOUT = 500;

function uuidv4() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c => (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16));
}

const WEBUI_CLIENT_KEY = uuidv4();

function changeDisplayedWorkflowType(workflowTypes, newWorkflowName) {
    const newWorkflowType = JSON.parse(workflowTypes)[newWorkflowName];
    const newIFrameElement = getWorkflowTypeIFrame(newWorkflowType);
    const oldIFrameElement = newIFrameElement.parentElement.querySelector(".comfyui-embedded-widget-display");
    oldIFrameElement.classList.remove("comfyui-embedded-widget-display");
    newIFrameElement.classList.add("comfyui-embedded-widget-display");
}

document.addEventListener("DOMContentLoaded", (e) => {
    onComfyuiTabLoaded(setupComfyuiTabEvents);
});

function onComfyuiTabLoaded(callback) {
    const textbox = getWorkflowIdsElement();
    const container = getComfyuiContainer();
    const tabNav = getTabNav();

    if (textbox === null || container === null || tabNav === null) {
        // webui not yet ready, try again in a bit
        setTimeout(() => { onComfyuiTabLoaded(callback); }, POLLING_TIMEOUT);
        return;
    }

    callback();
}

let WORKFLOW_TYPE_IDS = [];

function setupComfyuiTabEvents() {
    WORKFLOW_TYPE_IDS = JSON.parse(getWorkflowIdsElement().innerText);

    setupReloadOnErrorEvent();
    setupResizeTabEvent();
    setupToggleFooterEvent();

    updateComfyuiTabHeight();

    WORKFLOW_TYPE_IDS.forEach(id => forceFeedIdToIFrame(id));
}

function setupReloadOnErrorEvent() {
    WORKFLOW_TYPE_IDS.forEach(id => {
        const comfyuiFrame = getWorkflowTypeIFrame(id);
        comfyuiFrame.addEventListener("error", () => {
            setTimeout(() => {
                reloadFrameElement(comfyuiFrame);
            }, POLLING_TIMEOUT);
        });
    });
}

function reloadComfyuiIFrames() {
    WORKFLOW_TYPE_IDS.forEach(id => {
        const comfyuiFrame = getWorkflowTypeIFrame(id);
        reloadFrameElement(comfyuiFrame);
        forceFeedIdToIFrame(id);
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

function getWorkflowIdsElement() {
    return document.getElementById('comfyui_workflow_type_id_list') ?? null;
}

function getWorkflowTypeIFrame(workflowTypeId) {
    return document.querySelector(`[workflow_type_id="${workflowTypeId}"]`);
}

function getFooter() {
    return document.querySelector('#footer') ?? null;
}

function reloadFrameElement(iframeElement) {
    oldSrc = iframeElement.src;
    iframeElement.src = '';
    iframeElement.src = oldSrc;
}

function forceFeedIdToIFrame(workflowId) {
    let received = false;
    let messageToReceive = workflowId;

    window.addEventListener('message', (event) => {
        if(messageToReceive !== event.data) return;
        console.log(`[sd-webui-comfyui][webui] hs - ${event.data}`);
        received = true;
    });

    const feed = () => {
        if(received) return;
        const frameEl = getWorkflowTypeIFrame(workflowId);
        const targetOrigin = frameEl.src;
        const message = `${workflowId}.${WEBUI_CLIENT_KEY}`;
        frameEl.contentWindow.postMessage(message, targetOrigin);
        setTimeout(() => feed(), POLLING_TIMEOUT);
    };
    setTimeout(() => feed(), POLLING_TIMEOUT);
}
