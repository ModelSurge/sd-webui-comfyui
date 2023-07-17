import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";


async function longPolling() {
    try {
        console.log('try fetch');
        const response = await api.fetchApi("/request_press_queue_prompt_button", { cache: "no-store" });
        console.log(response);
        const json = await response.json();
        console.log(json);
        if (json.promptQueue) {
            console.log('prompt');
            app.queuePrompt(0, json.batchSize);
        }
    }
    catch (e) {
        console.log(e);
    }
    setTimeout(longPolling, 100);
}

longPolling();