mergeInto(LibraryManager.library, {

    JS_SaveStats: function(jsonPtr) {
        var json = UTF8ToString(jsonPtr);
        console.log('[StatsSync] JS_SaveStats called, length=' + json.length);
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/stats', false);
        xhr.setRequestHeader('Content-Type', 'application/json');
        try {
            xhr.send(json);
            if (xhr.status === 200) {
                console.log('[StatsSync] Stats saved to server');
            } else {
                console.error('[StatsSync] Save failed: ' + xhr.status);
            }
        } catch(e) {
            console.error('[StatsSync] Save error: ' + e);
        }
    },

    JS_LoadStats: function() {
        console.log('[StatsSync] JS_LoadStats called');
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/api/stats', false);
        try {
            xhr.send();
            if (xhr.status === 200 && xhr.responseText && xhr.responseText !== '{}') {
                console.log('[StatsSync] Loaded stats from server, length=' + xhr.responseText.length);
                var bufferSize = lengthBytesUTF8(xhr.responseText) + 1;
                var buffer = _malloc(bufferSize);
                stringToUTF8(xhr.responseText, buffer, bufferSize);
                return buffer;
            } else {
                console.log('[StatsSync] No stats on server (status=' + xhr.status + ')');
            }
        } catch(e) {
            console.error('[StatsSync] Load error: ' + e);
        }
        var empty = '{}';
        var bufSize = lengthBytesUTF8(empty) + 1;
        var buf = _malloc(bufSize);
        stringToUTF8(empty, buf, bufSize);
        return buf;
    },

    JS_DeleteStats: function() {
        console.log('[StatsSync] JS_DeleteStats called');
        var xhr = new XMLHttpRequest();
        xhr.open('DELETE', '/api/stats', false);
        try {
            xhr.send();
            console.log('[StatsSync] Stats deleted on server');
        } catch(e) {
            console.error('[StatsSync] Delete error: ' + e);
        }
    }

});
