

console.log('adding comfyui event');

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


function loadStyleProxy() {
    const comfyuiTab = document.getElementById('tab_comfyui_webui_root');

    // making sure the thing is loaded
    if(comfyuiTab === null || comfyuiTab === undefined) {
        setTimeout(loadStyleProxy, 200);
        return;
    }

    // Create a new MutationObserver instance
    const styleProxy = new Proxy(comfyuiTab.style, {
        set: function(target, property, value) {
            // Perform the original property assignment
            target[property] = value;

            // Handle the style change
            console.log("Style has changed for the element!");

            // Additional code to handle the style change goes here
            computeComfyuiElementHeight();

            // Indicate success
            return true;
        }
    });

    comfyuiTab.style = styleProxy;

    console.log('comfyui event added');

}


document.addEventListener("DOMContentLoaded", (e) => {
    computeComfyuiElementHeight();
});