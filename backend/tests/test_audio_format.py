from app.adapters.outbound.tts.audio_format import detect_audio_extension


def test_detects_wav_from_riff_header():
    data = b"RIFF" + b"\x00\x00\x00\x00" + b"WAVEfmt " + b"\x00" * 20
    assert detect_audio_extension(data) == ".wav"


def test_detects_mp3_from_id3_header():
    assert detect_audio_extension(b"ID3\x03\x00\x00\x00") == ".mp3"


def test_detects_mp3_from_frame_sync():
    assert detect_audio_extension(b"\xff\xfb\x90\x00") == ".mp3"


def test_detects_ogg():
    assert detect_audio_extension(b"OggS\x00\x02") == ".ogg"


def test_falls_back_to_default_for_unknown_bytes():
    assert detect_audio_extension(b"not audio at all") == ".mp3"
    assert detect_audio_extension(b"not audio at all", default=".bin") == ".bin"
