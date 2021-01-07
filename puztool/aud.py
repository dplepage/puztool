import io
import wave
import numpy as np
from IPython import display


def _extract_wav(reader):
    params = reader.getparams()
    frames = reader.readframes(params.nframes)
    print(f"{params.nchannels} channels, {params.sampwidth} bytes/sample")
    print(f"{params.nframes} frames at rate {params.framerate}")
    print(f"Returned array is {params.nframes}x{params.nchannels}"
          f", <i{params.sampwidth}")
    data = np.frombuffer(frames, dtype=f'<i{params.sampwidth}')
    if params.nchannels > 1:
        return data.reshape((-1, params.nchannels))
    return data


def load_wav(filename_or_fp):
    return _extract_wav(wave.open(filename_or_fp))


def parse_wav(raw_bytes):
    return load_wav(io.BytesIO(raw_bytes))


def disp(data, rate=44100):
    '''Display audio data in IPython.

    data can be 1D or have shape (nsamples, nchannels)
    '''
    return display.Audio(data.T, rate=rate)


def save_wav(data, filename, rate=44100):
    # ensure it's nsamp x nchannels
    data = data.reshape((data.shape[0], -1))
    with wave.open(filename, 'w') as writer:
        writer.setframerate(rate)
        writer.setsampwidth(data.dtype.itemsize)
        writer.setnchannels(data.shape[1])
        writer.writeframes(data.tobytes())
