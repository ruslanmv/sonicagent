import { MIC_CONSTRAINTS } from "./audio/capture";
import { nextDelayMs } from "./realtime/reconnect";

export function renderApp(root: HTMLElement): void {
  root.innerHTML = `<section><h1>SonicAgent</h1><p>Realtime capture asks the browser for echo cancellation, then sends 20 ms PCM frames.</p><button id="connect" type="button">Show capture settings</button><p id="status"></p></section>`;
  root.querySelector<HTMLButtonElement>("#connect")?.addEventListener("click", () => {
    const audio = MIC_CONSTRAINTS.audio;
    const echo = typeof audio === "object" && audio !== null && "echoCancellation" in audio ? String(audio.echoCancellation) : "false";
    const status = root.querySelector("#status");
    if (status) status.textContent = `Echo cancellation ${echo}. First reconnect waits ${nextDelayMs(0)} ms.`;
  });
}
