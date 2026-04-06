mergeInto(LibraryManager.library, {

    JS_GetPlayerName: function() {
        console.log('[ScoreSync] JS_GetPlayerName called');
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/api/player', false);
        try {
            xhr.send();
            if (xhr.status === 200) {
                var data = JSON.parse(xhr.responseText);
                var name = data.name || 'default';
                console.log('[ScoreSync] Player: ' + name);
                var bufferSize = lengthBytesUTF8(name) + 1;
                var buffer = _malloc(bufferSize);
                stringToUTF8(name, buffer, bufferSize);
                return buffer;
            }
        } catch(e) {
            console.error('[ScoreSync] GetPlayer error: ' + e);
        }
        var fallback = 'default';
        var bufSize = lengthBytesUTF8(fallback) + 1;
        var buf = _malloc(bufSize);
        stringToUTF8(fallback, buf, bufSize);
        return buf;
    },

    JS_GetMaxScore: function(usernamePtr, configPtr) {
        var username = UTF8ToString(usernamePtr);
        var config = UTF8ToString(configPtr);
        console.log('[ScoreSync] JS_GetMaxScore: ' + username + ' | ' + config);
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/api/scores/' + encodeURIComponent(username), false);
        try {
            xhr.send();
            if (xhr.status === 200) {
                var scores = JSON.parse(xhr.responseText);
                var maxScore = scores[config] || 0;
                console.log('[ScoreSync] Max score: ' + maxScore);
                return maxScore;
            }
        } catch(e) {
            console.error('[ScoreSync] GetMaxScore error: ' + e);
        }
        return 0;
    },

    JS_PostScore: function(usernamePtr, configPtr, mana) {
        var username = UTF8ToString(usernamePtr);
        var config = UTF8ToString(configPtr);
        console.log('[ScoreSync] JS_PostScore: ' + username + ' | ' + config + ' | ' + mana);
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/scores/' + encodeURIComponent(username), false);
        xhr.setRequestHeader('Content-Type', 'application/json');
        try {
            var body = JSON.stringify({config: config, mana: mana});
            xhr.send(body);
            if (xhr.status === 200) {
                var resp = JSON.parse(xhr.responseText);
                console.log('[ScoreSync] New record: ' + resp.new_record + ', max: ' + resp.max_mana);
                return resp.max_mana;
            }
        } catch(e) {
            console.error('[ScoreSync] PostScore error: ' + e);
        }
        return mana;
    },

    JS_DeleteScores: function(usernamePtr) {
        var username = UTF8ToString(usernamePtr);
        console.log('[ScoreSync] JS_DeleteScores: ' + username);
        var xhr = new XMLHttpRequest();
        xhr.open('DELETE', '/api/scores/' + encodeURIComponent(username), false);
        try {
            xhr.send();
            console.log('[ScoreSync] Scores deleted for ' + username);
        } catch(e) {
            console.error('[ScoreSync] DeleteScores error: ' + e);
        }
    }

});
