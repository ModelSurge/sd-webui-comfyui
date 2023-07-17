import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";


console.log('script launched');

async function longPolling() {
    try {
        const response = await api.fetchApi("/webui_request_queue_prompt", { cache: "no-store" });
        const json = await response.json();
        if (json.promptQueue) {
            app.queuePrompt(json.queueFront ? -1 : 0, json.batchCount);
        }
    }
    catch (e) {
        console.log(e);
    }
    setTimeout(longPolling, 0);
}

longPolling();