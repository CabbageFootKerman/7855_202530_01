(function () {
  "use strict";
  const deviceId = window.SMARTPOST_DEVICE_ID;

  const elDoor = document.getElementById("doorState");
  const elWeight = document.getElementById("weightValue");
  const elLast = document.getElementById("lastUpdate");
  const elCmd = document.getElementById("cmdResult");
  const elDebug = document.getElementById("debugBox");

  const cam1 = document.getElementById("cam1");
  const cam2 = document.getElementById("cam2");
  const cam3 = document.getElementById("cam3");

  const btnOpen = document.getElementById("btnOpen");
  const btnClose = document.getElementById("btnClose");

  const POLL_MS = 1000;

  function cacheBust(url) {
    const sep = url.includes("?") ? "&" : "?";
    return url + sep + "t=" + Date.now();
  }

  async function fetchState() {
    const res = await fetch(`/api/device/${encodeURIComponent(deviceId)}/state`, {
      method: "GET",
      credentials: "same-origin"
    });
    if (!res.ok) throw new Error(await res.text());
    return await res.json();
  }

  function render(data) {
    elDoor.textContent = data.door_state || "--";
    elWeight.textContent = (data.weight_g == null) ? "--" : String(data.weight_g) + " g";
    elLast.textContent = data.last_update_iso || "--";

    const cams = data.cameras || {};
    cam1.src = cacheBust(cams.cam1 || "");
    cam2.src = cacheBust(cams.cam2 || "");
    cam3.src = cacheBust(cams.cam3 || "");

    elDebug.textContent = JSON.stringify(data, null, 2);
  }

  async function sendCommand(cmd) {
    const res = await fetch(`/api/device/${encodeURIComponent(deviceId)}/command`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: cmd })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "Command failed");
    return data;
  }

  btnOpen.addEventListener("click", async () => {
    try {
      btnOpen.disabled = btnClose.disabled = true;
      const r = await sendCommand("open");
      elCmd.textContent = r.message || "Open sent";
    } catch (e) {
      elCmd.textContent = String(e.message || e);
    } finally {
      btnOpen.disabled = btnClose.disabled = false;
      setTimeout(() => { elCmd.textContent = ""; }, 3000);
    }
  });

  btnClose.addEventListener("click", async () => {
    try {
      btnOpen.disabled = btnClose.disabled = true;
      const r = await sendCommand("close");
      elCmd.textContent = r.message || "Close sent";
    } catch (e) {
      elCmd.textContent = String(e.message || e);
    } finally {
      btnOpen.disabled = btnClose.disabled = false;
      setTimeout(() => { elCmd.textContent = ""; }, 3000);
    }
  });

  async function loop() {
    try {
      render(await fetchState());
    } catch (e) {
      elDebug.textContent = String(e.message || e);
    }
    setTimeout(loop, POLL_MS);
  }

  loop();
})();
