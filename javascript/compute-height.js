function computeComfyuiElementHeight() {
    function getRecursiveParentNode(el, n) {
        if(n <= 0) return el;
        if(el === null || el.parentNode === null) return el;
        return getRecursiveParentNode(el.parentNode, n-1);
    }

    const parentDistance = 7;
    const container = document.getElementById("comfyui_webui_container");
    const dynamicElement = getRecursiveParentNode(container, parentDistance);

    if(dynamicElement !== null) {
        const height = dynamicElement.offsetHeight;
        container.style.height = `calc(100% - ${height-5}px)`;
    }

    // polling ew
    setTimeout(computeComfyuiElementHeight, 200);
}

document.addEventListener("DOMContentLoaded", (e) => {
    computeComfyuiElementHeight();
});
