mergeInto(LibraryManager.library, {

    // ---------------------------------------------------------------
    // AgentBridge.jslib — WebSocket bridge between Python gym and Unity
    // ---------------------------------------------------------------

    JS_AgentConnect: function(urlPtr) {
        var url = UTF8ToString(urlPtr);
        console.log('[AgentBridge] Connecting to ' + url);

        if (window._agentWS && window._agentWS.readyState <= 1) {
            console.log('[AgentBridge] Already connected, closing old connection');
            window._agentWS.close();
        }

        window._agentPendingCommands = [];
        window._agentConnected = false;

        var ws = new WebSocket(url);
        window._agentWS = ws;

        ws.onopen = function() {
            console.log('[AgentBridge] WebSocket connected');
            window._agentConnected = true;
            // Notify Unity that connection is ready
            if (window.unityInstance) {
                window.unityInstance.SendMessage('AgentBridge', 'OnConnected', '');
            }
        };

        ws.onmessage = function(event) {
            var msg = event.data;
            console.log('[AgentBridge] Received: ' + msg.substring(0, 200));
            // Forward command to Unity
            if (window.unityInstance) {
                window.unityInstance.SendMessage('AgentBridge', 'OnAgentCommand', msg);
            }
        };

        ws.onclose = function(event) {
            console.log('[AgentBridge] WebSocket closed: ' + event.code);
            window._agentConnected = false;
        };

        ws.onerror = function(error) {
            console.error('[AgentBridge] WebSocket error');
            window._agentConnected = false;
        };
    },

    JS_AgentSendMessage: function(jsonPtr) {
        var json = UTF8ToString(jsonPtr);
        if (window._agentWS && window._agentWS.readyState === 1) {
            window._agentWS.send(json);
        } else {
            console.warn('[AgentBridge] Cannot send, WebSocket not connected');
        }
    },

    JS_AgentSendScreenshot: function(seqNum) {
        var canvas = document.querySelector('#unity-canvas') || document.querySelector('canvas');
        if (!canvas) {
            console.error('[AgentBridge] No canvas found for screenshot');
            // Send error response
            if (window._agentWS && window._agentWS.readyState === 1) {
                var errMsg = JSON.stringify({
                    seq: seqNum,
                    type: 'screenshot',
                    error: 'No canvas found'
                });
                window._agentWS.send(errMsg);
            }
            return;
        }

        // Use toDataURL for synchronous capture
        var dataUrl = canvas.toDataURL('image/png');
        var base64 = dataUrl.split(',')[1];

        var msg = JSON.stringify({
            seq: seqNum,
            type: 'screenshot',
            data: base64,
            width: canvas.width,
            height: canvas.height
        });

        if (window._agentWS && window._agentWS.readyState === 1) {
            window._agentWS.send(msg);
            console.log('[AgentBridge] Screenshot sent (' + canvas.width + 'x' + canvas.height + ')');
        }
    },

    JS_AgentIsConnected: function() {
        return window._agentConnected ? 1 : 0;
    },

    JS_AgentDisconnect: function() {
        if (window._agentWS) {
            window._agentWS.close();
            window._agentWS = null;
            window._agentConnected = false;
            console.log('[AgentBridge] Disconnected');
        }
    },

    JS_AgentGetUrlParam: function() {
        // Check if ?agent=true is in the URL. If so, return the WebSocket URL.
        var params = new URLSearchParams(window.location.search);
        var agentMode = params.get('agent');
        if (agentMode === 'true') {
            var wsUrl = params.get('ws') || ('ws://' + window.location.host + '/ws/game');
            console.log('[AgentBridge] URL param agent=true detected, ws=' + wsUrl);
            var bufferSize = lengthBytesUTF8(wsUrl) + 1;
            var buffer = _malloc(bufferSize);
            stringToUTF8(wsUrl, buffer, bufferSize);
            return buffer;
        }
        // Return empty string if not in agent mode
        var empty = '';
        var bufSize = lengthBytesUTF8(empty) + 1;
        var buf = _malloc(bufSize);
        stringToUTF8(empty, buf, bufSize);
        return buf;
    }

});
