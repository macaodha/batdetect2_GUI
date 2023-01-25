"""
You can clip your files so that they are shorter using this script. 
You need to specify the locations of the input files and where you want the 
shorter files to be saved. 

There are additional settings that allow you to specify the output duration 
and where in the file you start clipping from.      
"""

import argparse
import os
from pathlib import Path

import numpy as np

from batdetect2_gui import audio_utils as au
from batdetect2_gui import wavfile


def main(args):

    audio_files = list(Path(args["input_directory"]).rglob("*.wav")) + list(
        Path(args["input_directory"]).rglob("*.WAV")
    )
    ip_files = [os.path.join(aa.parent, aa.name) for aa in audio_files]

    print("Input directory   : " + args["input_directory"])
    print("Output directory  : " + args["output_directory"])
    print("Start time        : {}".format(args["start_time"]))
    print("Output duration   : {}".format(args["output_duration"]))
    print("Audio files found : {}".format(len(ip_files)))

    if len(ip_files) == 0:
        return False

    if not os.path.isdir(os.path.dirname(args["output_directory"])):
        os.makedirs(os.path.dirname(args["output_directory"]))

    for ii, ip_path in enumerate(ip_files):
        sampling_rate, ip_audio = au.load_audio_file(
            ip_path, args["time_expansion_factor"]
        )
        duration = ip_audio.shape[0] / sampling_rate

        st_time = args["start_time"]
        en_time = st_time + args["output_duration"]
        st_samp = int(st_time * sampling_rate)
        en_samp = np.minimum(int(en_time * sampling_rate), ip_audio.shape[0])

        op_audio = np.zeros(
            int(sampling_rate * args["output_duration"]), dtype=ip_audio.dtype
        )
        op_audio[: en_samp - st_samp] = ip_audio[st_samp:en_samp]

        op_file = os.path.basename(ip_path).replace(" ", "_")
        op_file_en = (
            "__{:.2f}".format(st_time) + "_" + "{:.2f}".format(en_time)
        )
        op_file = op_file[:-4] + op_file_en + ".wav"

        op_path = os.path.join(args["output_directory"], op_file)
        wavfile.write(op_path, sampling_rate, op_audio)

        print("\n{}\tIP: ".format(ii) + os.path.basename(ip_path))
        print("\tOP: " + os.path.basename(op_path))


if __name__ == "__main__":

    info_str = (
        "\nScript that extracts smaller segment of audio from a larger file.\n"
        + " Place the files that should be clipped into the input directory.\n"
    )

    print(info_str)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input_directory",
        type=str,
        help="Input directory containing the audio files",
    )
    parser.add_argument(
        "output_directory",
        type=str,
        help="Output directory the clipped audio files",
    )
    parser.add_argument(
        "--output_duration",
        default=2.0,
        type=float,
        help="Length of output clipped file (default is 2 seconds)",
    )
    parser.add_argument(
        "--start_time",
        type=float,
        default=0.0,
        help="Start time from which the audio file is clipped (deafult is 0.0)",
    )
    parser.add_argument(
        "--time_expansion_factor",
        type=int,
        default=1,
        help="The time expansion factor used for all files (default is 1)",
    )
    args = vars(parser.parse_args())

    main(args)
