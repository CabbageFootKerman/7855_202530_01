(function () {
  "use strict";

  const deviceId = window.SMARTPOST_DEVICE_ID;

  const elDoor = document.getElementById("doorState");
  const elWeight = document.getElementById("weightValue");
  const elLast = document.getElementById("lastUpdate");
  const elCmd = document.getElementById("cmdResult");
  const elDebug = document.getElementById("debugBox");

  const camImgs = {
    0: document.getElementById("cam0"),
    1: document.getElementById("cam1"),
    2: document.getElementById("cam2")
  };

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

    // Camera images are loaded on-demand via snapshot buttons, not here.

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


  // - Camera snapshot buttons (request-response via command queue) -
  async function requestSnapshot(camId) {
    // Queue a capture command for this camera
    await fetchJson(
      "/api/device/" + encodeURIComponent(deviceId) + "/command",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: "capture", camera_id: Number(camId) })
      }
    );
  }

  async function pollForImage(camId, maxAttempts) {
    var attempts = maxAttempts || 10;
    var url = "/media/device/" + encodeURIComponent(deviceId)
            + "/camera/" + camId + "/latest.jpg";
    for (var i = 0; i < attempts; i++) {
      await new Promise(function (r) { setTimeout(r, 1000); });
      var resp = await fetch(url, { credentials: "same-origin" });
      if (resp.ok) return await resp.blob();
    }
    return null;
  }

  document.querySelectorAll(".snap-btn").forEach(function (btn) {
    btn.addEventListener("click", async function () {
      var camId = btn.getAttribute("data-cam");
      var statusEl = document.getElementById("camStatus" + camId);
      var img = camImgs[Number(camId)];

      btn.disabled = true;
      if (statusEl) statusEl.textContent = "Requesting capture...";

      try {
        await requestSnapshot(camId);
        if (statusEl) statusEl.textContent = "Waiting for device...";

        var blob = await pollForImage(camId, 10);
        if (blob) {
          if (img) img.src = URL.createObjectURL(blob);
          if (statusEl) statusEl.textContent = "";
        } else {
          if (statusEl) statusEl.textContent = "Timed out waiting for snapshot.";
        }
      } catch (e) {
        if (statusEl) statusEl.textContent = String(e.message || e);
      } finally {
        btn.disabled = false;
      }
    });
  });


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