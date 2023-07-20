const POLLING_TIMEOUT = 500;

document.addEventListener("DOMContentLoaded", (e) => {
    onComfyuiTabLoaded(setupComfyuiTabEvents);
});


const iframeIds = [
    'comfyui_general_tab',
    'comfyui_postprocess_txt2img',
    'comfyui_postprocess_img2img'
];


function onComfyuiTabLoaded(callback) {
    const comfyui_document = getComfyuiContainer();
    const tab_nav = getTabNav();

    if (comfyui_document === null || tab_nav === null) {
        // webui not yet ready, try again in a bit
        setTimeout(() => { onComfyuiTabLoaded(callback); }, POLLING_TIMEOUT);
        return;
    }

    callback();
}

function setupComfyuiTabEvents() {
    setupReloadOnErrorEvent();
    setupResizeTabEvent();
    setupToggleFooterEvent();

    updateComfyuiTabHeight();

    iframeIds.forEach(id => forceFeedIdToIFrame(document.querySelector(`#${id}`)));
}

function setupReloadOnErrorEvent() {
    const comfyui_document = getComfyuiContainer();
    comfyui_document.addEventListener("error", () => {
        setTimeout(() => {
            reloadObjectElement(comfyui_document);
        }, POLLING_TIMEOUT);
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
    const tab_nav_bottom = getTabNav().getBoundingClientRect().bottom;
    container.style.height = `calc(100% - ${tab_nav_bottom}px)`;
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

function getComfyuiIFrameElement() {
    return document.getElementById("comfyui_general_tab") ?? null;
}

function getFooter() {
    return document.querySelector('#footer') ?? null;
}

function reloadObjectElement(objectElement) {
    objectElement.src = objectElement.src;
}

function forceFeedIdToIFrame(frameEl) {
    let received = false;
    let messageToReceive = frameEl.getAttribute('id');

    window.addEventListener('message', (event) => {
        if(messageToReceive !== event.data) return;
        console.log(`[sd-webui-comfyui][webui] hs - ${event.data}`);
        received = true;
    });

    const feed = () => {
        if(received) return;
        const targetOrigin = frameEl.src;
        const message = frameEl.getAttribute('id');
        frameEl.contentWindow.postMessage(message, targetOrigin);
        setTimeout(() => { feed(); }, 100);
    };
    feed();
}