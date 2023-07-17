const POLLING_TIMEOUT = 500;

document.addEventListener("DOMContentLoaded", (e) => {
    onComfyuiTabLoaded(setupComfyuiTabEvents);
});

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
    // starts the comfyui js extension as soon as possible
    forceLoadObjectElement();

    setupReloadOnErrorEvent();
    setupResizeTabEvent();
    setupToggleFooterEvent();

    updateComfyuiTabHeight();
}

function forceLoadObjectElement() {
    const objectEl = getComfyuiObjectElement();
    if(objectEl === null) return;

    objectEl.style.visibility = 'hidden';
    const comfyuiTab = getComfyuiTab();
    objectEl.addEventListener('load', () => {
        comfyuiTab.style.display = 'none';
        objectEl.style.visibility = 'visible';
    });
    comfyuiTab.style.display = 'block';
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

function getComfyuiObjectElement() {
    return document.getElementById("comfyui_webui_root") ?? null;
}

function getFooter() {
    return document.querySelector('#footer') ?? null;
}

function reloadObjectElement(objectElement) {
    objectElement.data = objectElement.data;
}
