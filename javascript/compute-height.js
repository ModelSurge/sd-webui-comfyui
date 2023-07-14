function computeComfyuiElementHeight() {
    const tab = document.getElementById("tab_comfyui_webui_root");
    const container = document.getElementById("comfyui_webui_container");
    const footerToRemove = document.querySelector('#footer');
    const tabs = document.getElementById("tabs") ?? null;
    const tab_nav = tabs ? tabs.querySelector(".tab-nav") : null;

    if(tab_nav !== null) {
        const height = tab_nav.getBoundingClientRect().bottom;
        container.style.height = `calc(100% - ${height}px)`;
        updateFooterStyle(tab.style.display, footerToRemove);
    }

    // polling ew
    setTimeout(computeComfyuiElementHeight, 200);
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
    computeComfyuiElementHeight();
});
