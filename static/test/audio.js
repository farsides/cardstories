var root = '#cardstories_audio_example';

function setup() {
    $(root).cardstories_audio();
}

module("cardstories_audio", {setup: setup});

asyncTest("init", 2, function() {
    soundManager.onready(function() {
        var meta = $(root).data('sounds');
        var initialized_sounds = $(root).data('cardstories_audio').sounds;

        // Only the 'ring' sound is defined in the root metadata.
        // Expect a SoundManager sound object to be initialized.
        var sound = initialized_sounds['ring'];
        equal(sound.url, meta['ring'], 'sets the url from metadata');
        ok(sound.play, 'initialized object has a "play" method');
        start();
    });
});

asyncTest("play", 1, function() {
    soundManager.onready(function() {
        var sound = $(root).data('cardstories_audio').sounds['ring'];
        sound.play = function() { ok(true, 'play called'); };
        $.cardstories_audio.play('ring', root);
        try {
            $.cardstories_audio.play('ohoh', root);
        } catch(err) {
            ok(false, 'this should never happen');
        }
        start();
    });
});
