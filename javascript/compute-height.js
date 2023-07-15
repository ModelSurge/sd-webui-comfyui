const POLLING_TIMEOUT = 500;

function initComfyuiTabUpdateLoop() {
    const comfyui_document = document.getElementById("comfyui_webui_root") ?? null;
    const tab_nav = getTabNav();

    if (comfyui_document === null || tab_nav === null) {
        // polling ew
        setTimeout(initComfyuiTabUpdateLoop, POLLING_TIMEOUT);
        return;
    }

    comfyui_document.addEventListener("error", () => {
        setTimeout(() => {
            reloadObjectElementData(comfyui_document);
        }, POLLING_TIMEOUT);
    });

    // polling eww
    setTimeout(updateComfyuiTab, POLLING_TIMEOUT);
}

function updateComfyuiTab() {
    const tab = document.getElementById("tab_comfyui_webui_root");
    const footerToRemove = document.querySelector('#footer');
    updateFooterStyle(tab.style.display, footerToRemove);

    const container = document.getElementById("comfyui_webui_container");
    const tab_nav_bottom = getTabNav().getBoundingClientRect().bottom;
    container.style.height = `calc(100% - ${tab_nav_bottom}px)`;

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

function getTabNav() {
    const tabs = document.getElementById("tabs") ?? null;
    return tabs ? tabs.querySelector(".tab-nav") : null;
}

function reloadObjectElementData(objectElement) {
    objectElement.data = objectElement.data;
}

document.addEventListener("DOMContentLoaded", (e) => {
    initComfyuiTabUpdateLoop();
});
