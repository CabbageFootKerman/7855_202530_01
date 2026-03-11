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
    if (!url) return "";
    const sep = url.includes("?") ? "&" : "?";
    return url + sep + "t=" + Date.now();
  }

  function formatTimestamp(iso) {
    if (!iso) return "--";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString();
  }

  function formatWeight(value) {
    if (value == null) return "--";
    const n = Number(value);
    if (Number.isNaN(n)) return String(value) + " g";
    return n.toFixed(1) + " g";
  }

  async function fetchJson(url, options) {
    const res = await fetch(url, {
      credentials: "same-origin",
      ...(options || {})
    });

    let data = null;
    try {
      data = await res.json();
    } catch (_) {
      data = null;
    }

    if (!res.ok) {
      const msg = data && data.error ? data.error : "HTTP " + res.status;
      throw new Error(msg);
    }

    return data;
  }

  async function fetchState() {
    return await fetchJson(
      "/api/device/" + encodeURIComponent(deviceId) + "/state",
      { method: "GET" }
    );
  }

  function render(data) {
    if (elDoor) {
      elDoor.textContent = data.door_state || "--";
    }

    if (elWeight) {
      elWeight.textContent = formatWeight(data.weight_g);
    }

    if (elLast) {
      elLast.textContent = formatTimestamp(data.last_update_iso);
    }

    const cams = data.cameras || {};

    /*
      This supports either backend style:
      - cam0, cam1, cam2
      or
      - cam1, cam2, cam3

      HTML ids stay as cam1/cam2/cam3.
    */
    const cam1Url = cams.cam0 || cams.cam1 || "";
    const cam2Url = cams.cam1 || cams.cam2 || "";
    const cam3Url = cams.cam2 || cams.cam3 || "";

    if (cam1) {
      cam1.src = cacheBust(cam1Url);
    }
    if (cam2) {
      cam2.src = cacheBust(cam2Url);
    }
    if (cam3) {
      cam3.src = cacheBust(cam3Url);
    }

    if (elDebug) {
      elDebug.textContent = JSON.stringify(data, null, 2);
    }
  }

  async function sendCommand(cmd) {
    return await fetchJson(
      "/api/device/" + encodeURIComponent(deviceId) + "/command",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: cmd })
      }
    );
  }

  async function handleCommand(cmd) {
    try {
      if (btnOpen) btnOpen.disabled = true;
      if (btnClose) btnClose.disabled = true;

      if (elCmd) {
        elCmd.textContent = "Sending '" + cmd + "'...";
      }

      const result = await sendCommand(cmd);

      if (elCmd) {
        elCmd.textContent = result.message || ("Command '" + cmd + "' sent.");
      }

      const state = await fetchState();
      render(state);
    } catch (e) {
      if (elCmd) {
        elCmd.textContent = String((e && e.message) || e);
      }
    } finally {
      if (btnOpen) btnOpen.disabled = false;
      if (btnClose) btnClose.disabled = false;

      setTimeout(function () {
        if (elCmd) {
          elCmd.textContent = "";
        }
      }, 3000);
    }
  }

  if (btnOpen) {
    btnOpen.addEventListener("click", function () {
      handleCommand("open");
    });
  }

  if (btnClose) {
    btnClose.addEventListener("click", function () {
      handleCommand("close");
    });
  }

  async function loop() {
    try {
      const data = await fetchState();
      render(data);
    } catch (e) {
      if (elDebug) {
        elDebug.textContent = "State load failed: " + String((e && e.message) || e);
      }
    }

    setTimeout(loop, POLL_MS);
  }

  loop();
})();