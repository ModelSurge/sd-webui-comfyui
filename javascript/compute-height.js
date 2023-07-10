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
    const container = document.getElementById("comfyui_webui_container");
    const footerToRemove = document.querySelector('#footer');
    const dynamicElement = getDynamicElementFromContainer(container);

    if(dynamicElement !== null) {
        const height = dynamicElement.offsetHeight;
        container.style.height = `calc(100% - ${height-TAB_OFFSET_PADDING}px)`;
        footerToRemove.style.display = 'none';
    }

    // polling ew
    setTimeout(computeComfyuiElementHeight, 200);
}

document.addEventListener("DOMContentLoaded", (e) => {
    computeComfyuiElementHeight();
});
