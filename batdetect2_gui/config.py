"""
Configuration parameters
"""

SECRET_KEY = "INSERT_SECRET_KEY_HERE"

# constants for spectrogram generation
PARAMS = {}
PARAMS["fft_win_length"] = 2048 / 500000
PARAMS["win_length_units"] = "seconds"
PARAMS["fft_overlap"] = 0.9
PARAMS["max_freq"] = 150800  # round(fft_win_length*max_freq) == 700 pixels
PARAMS["min_freq"] = 0  # this should be kept at 0
PARAMS["resize_factor"] = 1.0
PARAMS[
    "playback_time_expansion"
] = 10  # files will be slowed down by this much

CACHE_SIZE = 10  # needs to be at least 3

# append to these lists if there is anything else you want to be able to annotate
EVENT_NAMES = ["Unknown", "Social", "Feeding", "Echolocation"]

CLASS_NAMES = ["Bat", "Not Bat", "Unknown"]
