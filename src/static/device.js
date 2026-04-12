(function () {
  "use strict";

  const deviceId = window.SMARTPOST_DEVICE_ID;

  const elDoor = document.getElementById("doorState");
  const elWeight = document.getElementById("weightValue");
  const elLast = document.getElementById("lastUpdate");
  const elCmd = document.getElementById("cmdResult");
  const elDebug = document.getElementById("debugBox");
  const elPageMessage = document.getElementById("pageMessage");

  let commandBusy = false;
  let lastStateError = "";
  let clearCmdTimer = null;

  const camImgs = {
    0: document.getElementById("cam0"),
    1: document.getElementById("cam1"),
    2: document.getElementById("cam2")
  };

  const btnOpen = document.getElementById("btnOpen");
  const btnClose = document.getElementById("btnClose");

  const POLL_MS = 5000;
  let authRedirecting = false;
  let pollingStopped = false;

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

    function normalizeDoorState(data) {
        return (
            data?.door_state ||
            data?.doorState ||
            data?.state ||
            "--"
        );
    }

    function getWeightValue(data) {
        return (
            data?.weight_g ??
            data?.weight ??
            data?.package_weight_g ??
            null
        );
    }

    function getLastUpdateValue(data) {
        return (
            data?.last_update_iso ||
            data?.updated_at ||
            data?.timestamp ||
            data?.last_seen ||
            null
        );
    }

    function getStateError(data) {
        if (!data) return "";
        if (data.error) return String(data.error);
        if (data.device_error) return String(data.device_error);
        if (data.online === false) return "Device offline";
        if (data.connected === false) return "Device disconnected";
        return "";
    }

    function setCmdMessage(message) {
        if (!elCmd) return;
        elCmd.textContent = message || "";
    }

    function clearCmdMessageLater() {
        if (clearCmdTimer) {
            clearTimeout(clearCmdTimer);
        }

        clearCmdTimer = setTimeout(function () {
            if (!commandBusy && !lastStateError && elCmd) {
                elCmd.textContent = "";
            }
        }, 3000);
    }

    function updateControls(data, loading) {
        const doorState = normalizeDoorState(data).toLowerCase();
        const offline = data && (data.online === false || data.connected === false);
        const busy = !!(data && (data.command_pending || data.busy));

        if (btnOpen) {
            btnOpen.disabled = !!loading || !!offline || !!busy || doorState === "open";
        }

        if (btnClose) {
            btnClose.disabled = !!loading || !!offline || !!busy || doorState === "closed";
        }
    }

    function renderStateError(message) {
        lastStateError = message || "";

        if (elDebug && message) {
            elDebug.textContent = "State load failed: " + message;
        }

        if (!commandBusy) {
            setCmdMessage(lastStateError);
        }
    }

    function showPageMessage(message, level) {
        if (!elPageMessage) return;
        elPageMessage.textContent = message || "";
        elPageMessage.classList.remove("hidden", "info", "error");
        elPageMessage.classList.add(level === "info" ? "info" : "error");
    }

    function clearPageMessage() {
        if (!elPageMessage) return;
        elPageMessage.textContent = "";
        elPageMessage.classList.add("hidden");
        elPageMessage.classList.remove("info", "error");
    }

    function setSnapshotButtonsDisabled(disabled) {
        document.querySelectorAll(".snap-btn").forEach(function (btn) {
            btn.disabled = disabled;
        });
    }

    function makeHttpError(status) {
        const err = new Error();
        err.status = status;
        err.isAuthError = status === 401 || status === 403;

        if (err.isAuthError) {
            err.message = "Your session has expired. Redirecting to login...";
        } else if (status === 404) {
            err.message = "Requested device data could not be found.";
        } else if (status >= 500) {
            err.message = "A server error occurred. Please try again.";
        } else {
            err.message = "Request failed. Please try again.";
        }

        return err;
    }

    function handleAuthFailure() {
        if (authRedirecting) return;

        authRedirecting = true;
        pollingStopped = true;

        updateControls({ online: false }, false);
        setSnapshotButtonsDisabled(true);
        showPageMessage("Your session has expired. Redirecting to login...", "info");

        if (elCmd) {
            elCmd.textContent = "Please sign in again.";
        }

        if (elDebug) {
            elDebug.textContent = "Authentication required.";
        }

        setTimeout(function () {
            window.location.href = "/login";
        }, 1500);
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
            throw makeHttpError(res.status);
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
        const doorState = normalizeDoorState(data);
        const weightValue = getWeightValue(data);
        const lastUpdate = getLastUpdateValue(data);
        const stateError = getStateError(data);

        if (elDoor) {
            elDoor.textContent = doorState;
        }

        if (elWeight) {
            elWeight.textContent = formatWeight(weightValue);
        }

        if (elLast) {
            elLast.textContent = formatTimestamp(lastUpdate);
        }

        updateControls(data, false);

        if (stateError) {
            renderStateError(stateError);
        } else {
            lastStateError = "";
            if (!commandBusy) {
                setCmdMessage("");
            }
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
            commandBusy = true;
            clearPageMessage();
            updateControls({ busy: true }, false);

            setCmdMessage("Sending '" + cmd + "'...");

            const result = await sendCommand(cmd);

            setCmdMessage(result.message || ("Command '" + cmd + "' sent."));

            const state = await fetchState();
            render(state);
            clearCmdMessageLater();
        } catch (e) {
            if (e && e.isAuthError) {
                handleAuthFailure();
                return;
            }

            showPageMessage("Unable to send the command right now.", "error");
            setCmdMessage("Command failed. Please try again.");
            clearCmdMessageLater();
        } finally {
            commandBusy = false;
            if (!authRedirecting) {
                updateControls(null, true);
            }
        }
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
        if (e && e.isAuthError) {
          handleAuthFailure();
          return;
        }

        showPageMessage("Unable to capture a snapshot right now.", "error");
        if (statusEl) statusEl.textContent = "Snapshot failed. Please try again.";
      } finally {
        btn.disabled = false;
      }
    });
  });



        async function loop() {
        if (pollingStopped) return;

        try {
            updateControls(null, true);

            const data = await fetchState();
            clearPageMessage();
            render(data);
        } catch (e) {
            if (e && e.isAuthError) {
                handleAuthFailure();
                return;
            }

            showPageMessage("Live device data is temporarily unavailable.", "error");

            if (elDebug) {
                elDebug.textContent = "State unavailable.";
            }

            updateControls({ online: false }, false);
        } finally {
            if (!pollingStopped) {
                setTimeout(loop, POLL_MS);
            }
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

    loop();
})();