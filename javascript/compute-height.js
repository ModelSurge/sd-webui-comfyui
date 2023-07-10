const TAB_OFFSET_PADDING = 5;

function getRecursiveParentNode(el, n) {
    if(n <= 0) return el;
    if(el === null || el.parentNode === null) return el;
    return getRecursiveParentNode(el.parentNode, n-1);
}

const getDynamicElementFromContainer = (container) => {
    const webuiParentDepth = 7;
    return getRecursiveParentNode(container, webuiParentDepth);
}

function computeComfyuiElementHeight() {
    const tab = document.getElementById("tab_comfyui_webui_root");
    const container = document.getElementById("comfyui_webui_container");
    const footerToRemove = document.querySelector('#footer');
    const dynamicElement = getDynamicElementFromContainer(container);

    if(dynamicElement !== null) {
        const height = dynamicElement.offsetHeight;
        container.style.height = `calc(100% - ${height-TAB_OFFSET_PADDING}px)`;
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
