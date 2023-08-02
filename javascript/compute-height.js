const POLLING_TIMEOUT = 500;

function uuidv4() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c => (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16));
}

const CLIENT_KEY = uuidv4();
const FRAME_IDS = [
    'comfyui_general_tab',
    'comfyui_postprocess_txt2img',
    'comfyui_postprocess_img2img',
    'comfyui_preprocess_latent_img2img',
];

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
    setupReloadOnErrorEvent();
    setupResizeTabEvent();
    setupToggleFooterEvent();

    updateComfyuiTabHeight();

    FRAME_IDS.forEach(id => forceFeedIdToIFrame(id));
}

function setupReloadOnErrorEvent() {
    FRAME_IDS.forEach(id => {
        const comfyui_frame = document.querySelector(`#${id}`);
        comfyui_frame.addEventListener("error", () => {
            setTimeout(() => {
                reloadFrameElement(comfyui_frame);
            }, POLLING_TIMEOUT);
        });
    });
}

function reloadComfyuiIFrames() {
    FRAME_IDS.forEach(id => {
        const comfyui_frame = document.querySelector(`#${id}`);
        reloadFrameElement(comfyui_frame);
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
    return document.querySelector('comfyui_general_tab') ?? null;
}

function getFooter() {
    return document.querySelector('#footer') ?? null;
}

function reloadFrameElement(iframeElement) {
    oldSrc = iframeElement.src;
    iframeElement.src = '';
    iframeElement.src = oldSrc;
}

function forceFeedIdToIFrame(frameId) {
    let received = false;
    let messageToReceive = frameId;

    window.addEventListener('message', (event) => {
        if(messageToReceive !== event.data) return;
        console.log(`[sd-webui-comfyui][webui] hs - ${event.data}`);
        received = true;

    });

    const feed = () => {
        if(received) return;
        const frameEl = document.querySelector(`#${frameId}`);
        const targetOrigin = frameEl.src;
        const message = `${frameEl.getAttribute('id')}.${CLIENT_KEY}`;
        frameEl.contentWindow.postMessage(message, targetOrigin);
        setTimeout(() => feed(), POLLING_TIMEOUT);
    };
    setTimeout(() => feed(), POLLING_TIMEOUT);
}
