import numpy as np
from PIL import Image
import wavfile
import warnings


def generate_spectrogram(audio, sampling_rate, params):
    """Creates an spectrogram image

    :param audio (array):
    :param sampling_rate (int):
    :param params (dict):
    :return: np.array
    """

    min_freq = 0

    # create spectrogram
    if params["win_length_units"] == "seconds":
        win_length_samples = int(params["fft_win_length"] * sampling_rate)
    else:
        win_length_samples = params["fft_win_length"]

    max_freq_bin = int(
        round(params["max_freq"] * (win_length_samples / sampling_rate))
    )

    spec = gen_mag_spectrogram(
        audio, sampling_rate, win_length_samples, params["fft_overlap"]
    )
    spec_orig_height = spec.shape[0]
    if spec.shape[0] < max_freq_bin:
        freq_pad = max_freq_bin - spec.shape[0]
        spec = np.vstack((np.zeros((freq_pad, spec.shape[1])), spec))

    spec = spec[-max_freq_bin : spec.shape[0] - min_freq, :]

    spec = spec.astype(np.float32)
    # todo: log frequency scale? would need to have a different axis and everything.
    # log_scaling = 2.0 * (1.0 / sampling_rate) * (1.0/(np.abs(np.hanning(int(params['fft_win_length']*sampling_rate)))**2).sum())
    # spec = np.log(1.0 + log_scaling*spec)
    spec = np.log(1.0 + spec)

    # denoise
    spec = spec - np.mean(spec, 1)[:, np.newaxis]  # denoise
    spec.clip(min=0, out=spec)

    # resize spectrogram
    if params["resize_factor"] != 1.0:
        op_width = int(spec.shape[1] * params["resize_factor"])
        op_height = int(spec.shape[0] * params["resize_factor"])
        spec = np.array(
            Image.fromarray(spec).resize(
                (op_width, op_height), resample=Image.BILINEAR
            )
        )

    return spec


def load_audio_file(audio_file, time_exp_fact):
    """reads audio file from disk and returns the array of samples

    :param audio_file (string):
    :param time_exp_fact (int): divide the sample rate by this number. 1 is converted to 10 (not sure why, or what to do if you actually want 1)
    :return: (int) original sampling rate of audio, (array) audio samples
    """
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=wavfile.WavFileWarning)
        sampling_rate, audio_raw = wavfile.read(audio_file)
    assert len(audio_raw.shape) == 1  # throw error if there is a stereo file
    sampling_rate = sampling_rate * time_exp_fact
    return sampling_rate, audio_raw


def pad_audio(audio_raw, fs, ms, overlap_perc, resize_factor, divide_factor):
    # adds zeros to the end of the raw data so that the generated spectrogram
    # will be evenly divisible by `divide_factor`
    nfft = int(ms * fs)
    noverlap = int(overlap_perc * nfft)
    step = nfft - noverlap
    spec_width = ((audio_raw.shape[0] - noverlap) // step) * resize_factor

    if (np.floor(spec_width) % divide_factor) != 0:
        target_size = int(
            np.ceil(spec_width / float(divide_factor))
            * divide_factor
            * (1.0 / resize_factor)
        )
        diff = target_size * step + noverlap - audio_raw.shape[0]
        audio_raw = np.hstack((audio_raw, np.zeros(diff).astype(np.float32)))

    return audio_raw


def gen_mag_spectrogram_fft(x, nfft, noverlap):
    """
    Compute magnitude spectrogram by specifying num bins.
    """

    # window data
    step = nfft - noverlap
    shape = (nfft, (x.shape[-1] - noverlap) // step)
    strides = (x.strides[0], step * x.strides[0])
    x_wins = np.lib.stride_tricks.as_strided(x, shape=shape, strides=strides)

    # apply window
    x_wins_han = np.hanning(x_wins.shape[0])[..., np.newaxis] * x_wins

    # do fft
    # TODO is this correct now that its switched to rfft?
    complex_spec = np.fft.rfft(x_wins_han, n=nfft, axis=0)

    # calculate magnitude
    mag_spec = np.conjugate(complex_spec) * complex_spec
    mag_spec = mag_spec.real
    # same as:
    # mag_spec = np.square(np.absolute(complex_spec))

    # orient correctly and remove dc component
    mag_spec = mag_spec[1:, :]
    mag_spec = np.flipud(mag_spec)

    return mag_spec


def gen_mag_spectrogram(x, fs, nfft, overlap_perc):
    """Computes magnitude spectrogram by specifying time.
    :param x np.array: the audio wave samples
    :param fs (int): sampling_rate
    :param nfft (float): window length in samples
    :param overlap_perc (float): fft overlap - fraction of window size
    :return: np.array?
    """

    # fft windows size in samples
    # nfft = int(ms*fs)

    # fft overlap in samples
    noverlap = int(overlap_perc * nfft)

    # window data
    step = nfft - noverlap  # number of samples to move each time
    shape = (nfft, (x.shape[-1] - noverlap) // step)
    strides = (x.strides[0], step * x.strides[0])
    x_wins = np.lib.stride_tricks.as_strided(x, shape=shape, strides=strides)

    # apply window
    # todo: user-specified?
    x_wins_han = np.hanning(x_wins.shape[0])[..., np.newaxis] * x_wins

    # do fft
    # note this will be much slower if x_wins_han.shape[0] is not a power of 2
    complex_spec = np.fft.rfft(x_wins_han, axis=0)

    # calculate magnitude
    mag_spec = (np.conjugate(complex_spec) * complex_spec).real

    # orient correctly and remove dc component
    spec = mag_spec[1:, :]
    spec = np.flipud(spec)

    return spec
