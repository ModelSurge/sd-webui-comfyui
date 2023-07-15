const POLLING_TIMEOUT = 500;

function comfyuiTabLoopInit() {
    const comfyui_document = document.getElementById("comfyui_webui_root");
    const tabs = document.getElementById("tabs") ?? null;
    const tab_nav = tabs ? tabs.querySelector(".tab-nav") : null;

    if (tab_nav === null) {
        // polling ew
        setTimeout(comfyuiTabLoopInit, POLLING_TIMEOUT);
        return;
    }

    comfyui_document.onerror = () => {
        // reload the object tag
        comfyui_document.data = comfyui_document.data;
    };

    // polling eww
    setTimeout(updateComfyuiTab, POLLING_TIMEOUT);
}

function updateComfyuiTab() {
    const tab = document.getElementById("tab_comfyui_webui_root");
    const container = document.getElementById("comfyui_webui_container");
    const footerToRemove = document.querySelector('#footer');
    const tabs = document.getElementById("tabs") ?? null;
    const tab_nav = tabs ? tabs.querySelector(".tab-nav") : null;

    const height = tab_nav.getBoundingClientRect().bottom;
    container.style.height = `calc(100% - ${height}px)`;
    updateFooterStyle(tab.style.display, footerToRemove);

    // polling ewww
    setTimeout(updateComfyuiTab, POLLING_TIMEOUT);
}

function updateFooterStyle(tabDisplay, footer) {
    if(footer === null) return;
    if(tabDisplay === 'block') {
        footer.classList.add('comfyui-remove-display');
    }
    else {
        footer.classList.remove('comfyui-remove-display');
    }
}

document.addEventListener("DOMContentLoaded", (e) => {
    comfyuiTabLoopInit();
});
