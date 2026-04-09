/* ─── Yedi Benchmark — shared dashboard helpers ─────────────────────── */
/* Vanilla JS, no build step. Loaded by base.html on every page.        */

(function () {
    "use strict";

    // ─── API client ─────────────────────────────────────────────────────

    async function apiRequest(method, path, body) {
        const opts = { method, headers: {} };
        if (body !== undefined) {
            opts.headers["Content-Type"] = "application/json";
            opts.body = JSON.stringify(body);
        }
        const res = await fetch(path, opts);
        const text = await res.text();
        let data = null;
        if (text) {
            try { data = JSON.parse(text); }
            catch (e) { data = text; }
        }
        if (!res.ok) {
            const detail = (data && data.detail) || res.statusText || "Request failed";
            const err = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
            err.status = res.status;
            err.body = data;
            throw err;
        }
        return data;
    }

    const api = {
        get:    (p)        => apiRequest("GET",    p),
        post:   (p, body)  => apiRequest("POST",   p, body || {}),
        put:    (p, body)  => apiRequest("PUT",    p, body || {}),
        del:    (p)        => apiRequest("DELETE", p),
    };

    // ─── Toasts ─────────────────────────────────────────────────────────

    function toast(message, kind) {
        const host = document.getElementById("toast-host");
        if (!host) { console.log("[toast]", message); return; }
        const el = document.createElement("div");
        el.className = "toast toast-" + (kind || "info");
        el.textContent = message;
        host.appendChild(el);
        setTimeout(() => {
            el.style.transition = "opacity 0.2s";
            el.style.opacity = "0";
            setTimeout(() => el.remove(), 250);
        }, 3500);
    }

    function toastError(err) {
        const msg = (err && err.message) || String(err);
        toast(msg, "error");
        console.error(err);
    }

    // ─── Modal helpers ──────────────────────────────────────────────────

    function openModal(id) {
        const m = document.getElementById(id);
        if (m) m.classList.add("is-open");
    }

    function closeModal(id) {
        const m = document.getElementById(id);
        if (m) m.classList.remove("is-open");
    }

    // Click outside the modal-window to close. Requires the backdrop element
    // to have data-close-on-backdrop and the inner .modal to stop propagation.
    function wireBackdropClose() {
        document.querySelectorAll(".modal-backdrop[data-close-on-backdrop]").forEach((bd) => {
            bd.addEventListener("click", (ev) => {
                if (ev.target === bd) bd.classList.remove("is-open");
            });
        });
    }

    // ─── DOM helpers ────────────────────────────────────────────────────

    function el(tag, attrs, children) {
        const node = document.createElement(tag);
        if (attrs) {
            for (const k of Object.keys(attrs)) {
                const v = attrs[k];
                if (k === "class")        node.className = v;
                else if (k === "html")    node.innerHTML = v;
                else if (k === "text")    node.textContent = v;
                else if (k.startsWith("on") && typeof v === "function")
                    node.addEventListener(k.slice(2).toLowerCase(), v);
                else if (v === true)      node.setAttribute(k, "");
                else if (v !== false && v != null) node.setAttribute(k, v);
            }
        }
        if (children) {
            (Array.isArray(children) ? children : [children]).forEach((c) => {
                if (c == null) return;
                node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
            });
        }
        return node;
    }

    function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

    function fmtDate(ts) {
        if (ts == null) return "—";
        const d = typeof ts === "number" ? new Date(ts * 1000) : new Date(ts);
        if (isNaN(d.getTime())) return String(ts);
        return d.toLocaleString();
    }

    function fmtNum(n, digits) {
        if (n == null || Number.isNaN(n)) return "—";
        return Number(n).toFixed(digits == null ? 2 : digits);
    }

    function escapeHtml(s) {
        return String(s == null ? "" : s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    // ─── Sidebar pollers ────────────────────────────────────────────────
    // Two polled endpoints feed the left sidebar:
    //   - /api/runs/active   → "Active run" pill (and onActiveRunChange subs)
    //   - /api/bridge/status → "Game bridge" pill (green when a browser is
    //                          connected to /ws/game; red otherwise)

    const runStatusListeners = [];
    const bridgeStatusListeners = [];
    let lastActive = null;
    let lastBridge = null;

    function onActiveRunChange(cb)    { runStatusListeners.push(cb); }
    function onBridgeStatusChange(cb) { bridgeStatusListeners.push(cb); }

    async function pollActiveRun() {
        try {
            const data = await api.get("/api/runs/active");
            renderRunStatus(data);
            const sig = JSON.stringify(data);
            if (sig !== lastActive) {
                lastActive = sig;
                runStatusListeners.forEach((fn) => { try { fn(data); } catch (e) { console.error(e); } });
            }
        } catch (e) {
            renderRunStatus(null);
        }
    }

    async function pollBridgeStatus() {
        try {
            const data = await api.get("/api/bridge/status");
            renderBridgeStatus(data);
            const sig = JSON.stringify(data);
            if (sig !== lastBridge) {
                lastBridge = sig;
                bridgeStatusListeners.forEach((fn) => { try { fn(data); } catch (e) { console.error(e); } });
            }
        } catch (e) {
            renderBridgeStatus(null);
        }
    }

    function renderBridgeStatus(s) {
        const host = document.getElementById("bridge-status");
        const body = document.getElementById("bridge-status-body");
        if (!host || !body) return;
        host.classList.remove("is-ok", "is-err", "is-warn");
        if (!s) {
            body.textContent = "unreachable";
            host.classList.add("is-err");
            return;
        }
        if (s.game_connected) {
            // Hidden tab is still "connected" (the WebSocket is fine, the
            // WebGL main loop just gets throttled). We surface a warning
            // pill so the user can see the cause before bridge timeouts
            // start blowing up runs.
            if (s.tab_hidden) {
                host.classList.add("is-warn");
                body.innerHTML =
                    `<div>game: <strong>tab hidden</strong></div>` +
                    `<div class="dim">bring the game window forward</div>`;
            } else {
                host.classList.add("is-ok");
                body.innerHTML =
                    `<div>game: connected</div>` +
                    `<div>agent: ${s.agent_connected ? "connected" : "—"}</div>`;
            }
        } else {
            host.classList.add("is-err");
            body.innerHTML =
                `<div>game: <strong>not connected</strong></div>` +
                `<div class="dim">open the Game tab</div>`;
        }
    }

    function renderRunStatus(active) {
        const host = document.getElementById("run-status");
        const body = document.getElementById("run-status-body");
        if (!host || !body) return;
        if (active && active.active) {
            host.classList.add("is-running");
            const done = active.episodes_done || 0;
            const total = active.episodes_total || 0;
            const id = active.run_id || "—";
            body.innerHTML =
                `<div>${escapeHtml(id.slice(0, 8))}…</div>` +
                `<div>${done}/${total} ep</div>`;
            body.title = id;
        } else {
            host.classList.remove("is-running");
            body.textContent = "idle";
            body.title = "";
        }
    }

    function startSidebarPollers(intervalMs) {
        pollActiveRun();
        pollBridgeStatus();
        setInterval(pollActiveRun, intervalMs || 3000);
        setInterval(pollBridgeStatus, intervalMs || 3000);
    }

    // ─── Boot ───────────────────────────────────────────────────────────

    document.addEventListener("DOMContentLoaded", () => {
        wireBackdropClose();
        startSidebarPollers(3000);
    });

    // Expose to page-specific scripts
    window.YediApp = {
        api, toast, toastError,
        openModal, closeModal,
        el, clear, fmtDate, fmtNum, escapeHtml,
        onActiveRunChange, onBridgeStatusChange,
    };
})();
