import audio_utils as au
import os
from io import BytesIO
import base64
import matplotlib.pyplot as plt
from PIL import Image
import wavfile
import numpy as np


def compute_audio_data(annotation, audio_dir, playback_time_expansion):
    """returns the metadata, raw audio samples and base64 encoded wav file

    :param annotation (dict): dictionary containing annotations for a file
    :return (tuple):
      - (int) sample rate of audio
      - (array) audio samples
      - (string) base64 wav file
      - (float) file duration
    """
    # load wav
    wav_file_path = os.path.join(
        audio_dir, annotation["file_name"].replace(".json", "")
    )
    sampling_rate, audio_raw = au.load_audio_file(
        wav_file_path, annotation["time_exp"]
    )
    duration = audio_raw.shape[0] / float(sampling_rate)

    # apply time expansion if the file is high frequency
    time_exp_listen = annotation["time_exp"]
    if annotation["time_exp"] == 1:
        time_exp_listen = playback_time_expansion
    elif annotation["time_exp"] == playback_time_expansion:
        print("Correct time expansion already used.")
    else:
        raise Exception("Unsuported time expansion factor.")

    aud_file = BytesIO()
    wavfile.write(aud_file, int(sampling_rate / time_exp_listen), audio_raw)
    aud_data = base64.b64encode(aud_file.getvalue()).decode("utf-8")
    aud_file.close()

    return sampling_rate, audio_raw, aud_data, duration


def compute_image_data(audio_raw, sampling_rate, spec_params):
    """computes and returns a spectrogram image

    :param audio_raw (array): audio samples
    :param sampling_rate (int):
    :return (tuple):
      - (string) base64 spectrogram image
      - (tuple?) height,width in pixels
    """
    # generate spectrogram
    spec_raw = au.generate_spectrogram(audio_raw, sampling_rate, spec_params)
    spec_raw -= spec_raw.min()
    spec_raw /= spec_raw.max()
    cmap = plt.get_cmap("inferno")
    spec = (cmap(spec_raw)[:, :, :3] * 255).astype(np.uint8)

    # create output image
    im = Image.fromarray(spec)
    im_file = BytesIO()
    im.save(im_file, "JPEG", quality=90)
    im_data = base64.b64encode(im_file.getvalue()).decode("utf-8")
    im_file.close()

    return im_data, spec.shape
