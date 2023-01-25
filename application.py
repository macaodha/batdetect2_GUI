#!/usr/bin/env python
from __future__ import print_function
from flask import (
    Flask,
    session,
    request,
    render_template,
    redirect,
    copy_current_request_context,
)
import uuid
from pathlib import Path
import random
import json
import sys
from threading import Thread
import copy
import os
import time
import config
import generate_data as gd
import hashlib


application = Flask(__name__)
application.secret_key = config.SECRET_KEY

# array of datasets - contains paths, file_names, annotations, ...
datasets = {}

# cache for storing precomputed spectrograms
cache = {}


def hash_str(ip_str):
    return hashlib.md5(ip_str.encode("utf-8")).hexdigest()


def create_blank_annotation_file(file_name):
    """Creates a blank annotation dictionary for this file

    :param file_name (string):
    :return: (dict)
    """
    result_dict = {}
    if file_name.endswith(".json"):
        result_dict["id"] = os.path.basename(file_name[:-5])
    else:
        result_dict["id"] = os.path.basename(file_name)
    result_dict["file_name"] = file_name
    # this the complete file path
    result_dict["hash_id"] = hash_str(result_dict["file_name"])
    result_dict["annotated"] = False
    result_dict["issues"] = False
    result_dict["class_name"] = ""
    result_dict["notes"] = ""
    # time expansion for this file.
    # slow the audio by a factor of this when playing in browser
    result_dict["time_exp"] = 1
    result_dict["duration"] = -1
    result_dict["annotation"] = []
    return result_dict


@application.route("/clear_session")
def initialize_session(file_index=0):
    """clears the session and creates initialises a new one
    - new uuid, file_id is 0

    :return: None
    """
    print("initializing session")
    session.clear()
    session["spectrogram_params"] = config.PARAMS
    session["name"] = str(uuid.uuid4())
    session["user_name"] = "admin"
    session["dataset_id"] = "none"
    session[
        "file_index"
    ] = file_index  # int, keeps track of the index of the currently selected file
    session.modified = True

    return "session cleared"


@application.route("/clear_cache")
def initialize_cache():
    """clears the cache

    :return: None
    """
    global cache
    cache = {}
    return "cache cleared"


@application.route("/clear_datasets")
def initialize_datasets():
    """clears the datasets

    :return: None
    """
    global datasets
    datasets = {}
    return "datasets cleared"


def select_file(num_files, file_id=-1, next_file=False):
    """Selects the next file in the list to show

    :param file_id: requested id - checks if valid
    :param next_file (bool): whether to select the next file (overrides request)
    :return (int): The index of the selected file
    """
    if next_file:
        print("showing next file")
        file_id = 0 if file_id + 1 >= num_files else file_id + 1
    elif file_id > -1 and (file_id < num_files):
        print("showing requested file")
    else:
        print("showing random file")
        file_id = random.choice(num_files)

    return file_id


@application.route("/annotate/", methods=["POST"])
def submit_annotations():
    """Action for submitting the form"""

    if "name" not in session.keys():
        initialize_session()

    if not check_files_and_annotations():
        return redirect("/", code=302)

    dataset = datasets[session["dataset_id"]]

    # if there are some post variables and changes were made, update stuff
    if len(request.form) > 0 and json.loads(request.form["change_made"]):
        input_id = request.form["file_name"]
        dataset_id = request.form["dataset_id"]
        print("updating", input_id, "from", dataset_id)
        # TODO update the session with this dataset_id if different

        dataset["annotations"][input_id]["annotation"] = json.loads(
            request.form["updated_annotations"]
        )
        dataset["annotations"][input_id]["notes"] = str(request.form["notes"])
        dataset["annotations"][input_id]["annotated"] = True
        # dataset['annotations'][input_id]['user_name'] = session['user_name']

        if len(request.form.getlist("unsure")) > 0:
            dataset["annotations"][input_id]["issues"] = True
        else:
            dataset["annotations"][input_id]["issues"] = False

        # save to disk
        save_annotation(
            dataset["annotation_dir"], dataset["annotations"][input_id]
        )

        # add the submitted classes to the list, then sort them and remove duplicates
        this_file_class_list = set(
            [
                aa["class"]
                for aa in dataset["annotations"][input_id]["annotation"]
            ]
        )
        sorted_classes = sorted(
            list(
                this_file_class_list.union(set(dataset["class_names"]))
                - set(config.CLASS_NAMES)
            )
        )
        dataset["class_names"] = config.CLASS_NAMES + sorted_classes

    # redirect to the next item to annotate
    id = dataset["file_names"].index(request.form["file_name"])
    next_id = select_file(
        len(dataset["file_names"]), file_id=id, next_file=True
    )
    url_str = (
        "/annotate/?file_name="
        + dataset["file_names"][next_id]
        + "&dataset_id="
        + session["dataset_id"]
    )
    return redirect(url_str, code=302)


@application.route("/annotate/", methods=["GET"])
def render_annotation_page():
    """Action for annotate page requested with POST

    - initialises the session if it's not already set up
    - processes post data (annotation data from the previous file)
    - selects the next file and get the annotation data for it
    - gets data (for template) for file params, spectrogram image and audio
    - sets template data for the above, and annotation data, class, and event names

    :return (string): rendered template
    """

    default_file = 0
    if "name" not in session.keys():
        initialize_session(default_file)

    if (
        "dataset_id" in request.args
        and request.args["dataset_id"] in datasets.keys()
    ):
        session["dataset_id"] = request.args["dataset_id"]
        session.modified = True

    if not check_files_and_annotations():
        return redirect("/", code=302)

    dataset = datasets[session["dataset_id"]]

    if (
        "file_name" in request.args
        and request.args["file_name"] in dataset["file_names"]
    ):
        cur_file = dataset["file_names"].index(request.args["file_name"])
    else:
        cur_file = default_file

    # get next file to show
    file_index = select_file(len(dataset["file_names"]), file_id=cur_file)
    annotation = dataset["annotations"][dataset["file_names"][file_index]]
    session["file_index"] = file_index
    session.modified = True

    print("serving ", annotation["file_name"])
    file_params, im_data, aud_data = get_data(annotation, use_cache=True)
    next_file = dataset["file_names"][
        (cur_file + 1) % len(dataset["file_names"])
    ]
    prev_file = dataset["file_names"][
        (cur_file - 1) % len(dataset["file_names"])
    ]

    annotations_sorted = [
        dataset["annotations"][ff] for ff in dataset["file_names"]
    ]

    return render_template(
        "annotate.html",
        annotation=annotation,
        file_index=session["file_index"],
        next_file=next_file,
        prev_file=prev_file,
        dataset_id=session["dataset_id"],
        class_names=dataset["class_names"],
        event_names=dataset["event_names"],
        im_data=im_data,
        aud_data=aud_data,
        file_params=file_params,
        annotations=annotations_sorted,
        annotation_dir=dataset["annotation_dir"],
        audio_dir=dataset["audio_dir"],
        spectrogram_params=get_spectrogram_params(),
    )


@application.route("/", methods=["POST", "GET"])
@application.route("/index", methods=["POST", "GET"])
@application.route("/dataset_list", methods=["POST", "GET"])
def render_dataset_list_page():
    """Action for the dataset list page

    - initialize session
    - get annotation data for all files

    :return (string): rendered_template
    """
    if "name" not in session.keys():
        initialize_session()

    if len(request.form) > 0:
        annotation_dir = os.path.join(request.form["annotation_dir"], "")
        audio_dir = os.path.join(request.form["audio_dir"], "")
        session["dataset_id"] = create_dataset(audio_dir, annotation_dir)
        session.modified = True
        return redirect("/file_list", code=302)

    dataset_info = []
    for dd in datasets:
        dataset_info.append(
            {
                "dataset_id": dd,
                "annotation_dir": datasets[dd]["annotation_dir"],
                "audio_dir": datasets[dd]["audio_dir"],
                "num_files": len(datasets[dd]["annotations"]),
            }
        )

    return render_template("dataset_list.html", dataset_info=dataset_info)


@application.route("/file_list", methods=["POST", "GET"])
def render_file_list_page():
    """Action for the file list page

    - initialize session
    - get annotation data for all files

    :return (string): rendered_template
    """
    if "name" not in session.keys():
        initialize_session()

    if (
        "dataset_id" in request.args
        and request.args["dataset_id"] in datasets.keys()
    ):
        session["dataset_id"] = request.args["dataset_id"]
        session.modified = True

    if not check_files_and_annotations():
        return redirect("/", code=302)

    if session["dataset_id"] in datasets.keys():
        dataset = datasets[session["dataset_id"]]
        annotations_sorted = [
            dataset["annotations"][ff] for ff in dataset["file_names"]
        ]
        annotation_dir = dataset["annotation_dir"]
        audio_dir = dataset["audio_dir"]
    else:
        annotations_sorted = []
        annotation_dir = ""
        audio_dir = ""

    return render_template(
        "file_list.html",
        annotations=annotations_sorted,
        dataset_id=session["dataset_id"],
        annotation_dir=annotation_dir,
        audio_dir=audio_dir,
    )


@application.route("/spectrogram_params", methods=["GET", "POST"])
def set_spectrogram_params():
    """sets the spectrogram parameters e.g. overlap,window size etc
    :return: redirect
    """

    get_spectrogram_params()

    for pname in ["fft_win_length", "fft_overlap", "max_freq"]:
        if request_val(pname) is not None:
            session["spectrogram_params"][pname] = float(request_val(pname))
            session.modified = True

    if request_val("win_length_units") is not None:
        session["spectrogram_params"]["win_length_units"] = request_val(
            "win_length_units"
        )
        session.modified = True

    if session["spectrogram_params"]["win_length_units"] == "samples":
        session["spectrogram_params"]["fft_win_length"] = int(
            session["spectrogram_params"]["fft_win_length"]
        )
        session.modified = True

    url_str = (
        "/annotate/?file_name="
        + request_val("file_name")
        + "&dataset_id="
        + request_val("dataset_id")
    )
    return redirect(url_str, code=302)


def request_val(pname):
    """helper function to get a value passed via get or post requests
       while failing gracefully if missing

    :param name:
    :return (mixed): The value
    """

    if pname in request.form:
        return request.form[pname]
    elif pname in request.args:
        return request.args[pname]
    elif pname in request.json:
        return request.json[pname]
    else:
        return None


def get_spectrogram_params():
    """returns spectrogram params

    Either returns the session-stored spectrogram params, or if those
     have not been set, returns the the config-file ones.

    :return dict:
    """
    if not "spectrogram_params" in session.keys():
        session["spectrogram_params"] = config.PARAMS
        session.modified = True

    # validate
    invalid = False
    sp = session["spectrogram_params"]
    if sp["fft_win_length"] <= 0:
        invalid = True

    if sp["fft_win_length"] > 1 and sp["win_length_units"] == "seconds":
        # if something goes wrong and the win_length_units and win_length get mismatched
        invalid = True

    if invalid:
        session["spectrogram_params"] = config.PARAMS
        session.modified = True

    return session["spectrogram_params"]


def get_data(annotation, use_cache=True):
    """Gets file params, image and audio data for the page

    First checks the cache. If it's in the cache those values are used
    if not data is computed. Then, it caches the next file data asynchronously

    :param annotation (dict):
    :param use_cache (bool):
    :return (list?):
      - (dict) file params
      - (str) base64 encoded image
      - (str) base64 encoded audio file
    """
    # check if data has already been computed - if yes, return it
    dataset = datasets[session["dataset_id"]]
    cache_key = gen_cache_key(
        annotation["file_name"], get_spectrogram_params()
    )
    if use_cache:
        if cache_key in cache and cache[cache_key]["thread_lock"] is False:
            print("  using cached data for " + annotation["file_name"])
            file_params = cache[cache_key]["file_params"]
            im_data = cache[cache_key]["im_data"]
            aud_data = cache[cache_key]["aud_data"]
        else:
            # if it's not in the cache or is in the cache but not finished computing
            # compute it and store to cache.
            # if it was already in the process of being computed and stored, then whichever finishes
            # last will end up being stored, but they should be the same.
            file_params, im_data, aud_data = cache_item(annotation)

        update_cache(
            annotation["file_name"],
            dataset["file_names"],
            dataset["annotations"],
            dataset["audio_dir"],
        )

    else:
        # if no, compute from scratch
        file_params, im_data, aud_data = compute_data(
            annotation, dataset["audio_dir"]
        )

    return file_params, im_data, aud_data


def gen_cache_key(file_name, spec_params):
    """returns a string based on the file_name and the current spectrogram parameters

    :param file_name (str):
    :param spec_params  (dict):
    :return: str
    """

    # sort parameters and use them in the id
    # sorted dictionaries might not be available in early versions
    # so we need to do it in a way that includes a sort()
    param_string = "&".join(
        list("{}={}".format(key, value) for key, value in spec_params.items())
    )
    return str(file_name) + ":" + param_string


def cache_item(annotation):
    """computes an item, caches it, and returns it

    :param annotation:
    :return:
    """
    audio_dir = datasets[session["dataset_id"]]["audio_dir"]
    cache_key = gen_cache_key(
        annotation["file_name"], get_spectrogram_params()
    )

    # initialise cache item
    cache[cache_key] = {
        "id": annotation["file_name"],
        "thread_lock": True,
        "cache_key": cache_key,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    # compute required data for next timestep and store in global cache
    print("  caching " + annotation["file_name"])
    file_params, im_data, aud_data = compute_data(annotation, audio_dir)

    # there is a small chance this item took so long it's already been removed from the cache
    # in that case, don't add it to the cache (but do return it from this function)
    if cache_key in cache:
        cache[cache_key]["file_params"] = file_params
        cache[cache_key]["im_data"] = im_data
        cache[cache_key]["aud_data"] = aud_data
        cache[cache_key]["thread_lock"] = False

    return file_params, im_data, aud_data


def update_cache(file_id, file_names, annotations, audio_dir):
    """
    cache holds up to 3 files' data at once: the current file, the previous file and the next file
    This function checks if all three are set for the current file, and if not, generates them
    it removes any that are set for files other than those three files

    :return:
    """
    global cache
    file_index = file_names.index(file_id)

    next_index = (file_index + 1) % len(file_names)
    prev_index = (file_index - 1) % len(file_names)
    file_indexes_for_cache = [next_index, file_index, prev_index]

    # start thread for producing all of the cache_needed items
    # put this function in local scope to allow copy of request context
    # this is necessary to access the spectrogram_params in the session
    @copy_current_request_context
    def compute_cache_data(anns):
        """caches file params, spectogram, and image data for given file ids

        :param file_ids (list of strings):
        :return: null
        """
        for ann in anns:
            cache_item(ann)

    # select the items to cache
    anns_to_cache = []
    for f_id in file_indexes_for_cache:
        if (
            gen_cache_key(file_names[f_id], get_spectrogram_params())
            not in cache.keys()
        ):
            anns_to_cache.append(annotations[file_names[f_id]])

    # start one thread that computes 2 items in sequence, rather than 2 threads that compute them in parallel
    # it seems the 2nd option is unstable
    thread = Thread(target=compute_cache_data, kwargs={"anns": anns_to_cache})
    thread.start()

    # to save space, we remove the oldest items from the cache
    # size of cache is set in the config file
    cache_data = [
        {k: item[k] for k in ("cache_key", "created_at")}
        for item in cache.values()
    ]
    cache_data = sorted(cache_data, key=lambda item: item["created_at"])
    cache_size = max(config.CACHE_SIZE, 3)  # want to keep the most recent ones
    to_remove = cache_data[0 : max(len(cache_data) - cache_size, 0)]
    for item in to_remove:
        del cache[item["cache_key"]]
    print("size of cache: " + str(len(cache)))

    # older, better cache cleaning that made sure that recently generated items were not deleted
    # to_remove = [{k: item[k] for k in ('cache_key', 'created_at')} for item in cache.values()]
    # keep_cache_keys = [gen_cache_key(file_names[f_id], audio_dir, get_spectrogram_params()) for f_id in file_indexes_for_cache]
    # to_remove = [item for item in to_remove if item['cache_key'] not in keep_cache_keys]
    # # sort oldest first
    # to_remove = sorted(to_remove, key=lambda item: item['created_at'])
    # # keep at most this many items in addition to the important 3
    # keep = 3
    # to_remove = to_remove[0:max(len(to_remove) - keep, 0)]
    # print("Len(to_remove): " + str(len(to_remove)))
    # print("Len(cache): " + str(len(cache)))
    # for item in to_remove:
    #     del cache[item['cache_key']]


def compute_data(annotation, audio_dir):
    """returns the file params, image and audio data for the given annotation object

    File params are included here because some audio metadata like duration is
    extracted during processing

    :param annotation (dict): dict containing list of annotations for the file
    :return (tuple): (dict) file params, (str) base64 image, (str) base64 audio
    """
    tm_exp_play = config.PARAMS["playback_time_expansion"]
    sampling_rate, audio_raw, aud_data, duration = gd.compute_audio_data(
        annotation, audio_dir, tm_exp_play
    )
    im_data, im_shape = gd.compute_image_data(
        audio_raw, sampling_rate, get_spectrogram_params()
    )
    duration_listen = duration * config.PARAMS["playback_time_expansion"]

    # if the duration has not been provided with the file - then set it
    if annotation["duration"] == -1:
        annotation["duration"] = duration

    if get_spectrogram_params()["win_length_units"] == "seconds":
        win_length_secs = get_spectrogram_params()["fft_win_length"]
    else:
        win_length_secs = (
            float(get_spectrogram_params()["fft_win_length"]) / sampling_rate
        )

    file_params = {
        "fft_win_length_secs": win_length_secs,
        "fft_overlap": get_spectrogram_params()["fft_overlap"],
        "spec_height": im_shape[0],
        "spec_width": im_shape[1],
        "duration": duration,
        "sampling_rate": sampling_rate,
        "duration_listen": duration_listen,
    }

    return file_params, im_data, aud_data


def save_annotation(annotation_dir, ann):
    """Saves the annotation to json

    Json filename is based off the filename of the audio file the annotations
    belong to, which is stored in the ann dictionary

    :param ann (dict?): the annotations
    :return: null
    """
    op_file_name = os.path.join(annotation_dir, ann["file_name"])
    ann_to_save = copy.deepcopy(ann)
    del ann_to_save["file_name"]
    del ann_to_save["hash_id"]

    if not os.path.isdir(os.path.dirname(op_file_name)):
        os.makedirs(os.path.dirname(op_file_name))

    with open(op_file_name, "w") as da:
        json.dump(ann_to_save, da, indent=2, sort_keys=True)


def check_files_and_annotations():
    """Ensures file_names, annotations and directories are all set up

    Makes sure that whichever page the user tries to load first, things will work.
    If everything is loaded, this will be really fast.

    - first checks file_names to make sure we have some wav files
      - If it's empty, checks the audio directory
        - if that the path is not set or has no audio file, redirects to the index page
    - then, checks to make sure that the annotations directory has the correct number of annotations
      - if not loads the annotations

    :return (list): filenames
    """

    if len(datasets.keys()) == 0:
        return False
    elif session["dataset_id"] == "none":
        return False
    else:
        dataset = datasets[session["dataset_id"]]

    if len(dataset["file_names"]) == 0 or (
        len(dataset["annotations"]) != len(dataset["file_names"])
    ):

        if dataset["audio_dir"] != "" and dataset["annotation_dir"] != "":
            create_dataset(dataset["audio_dir"], dataset["annotation_dir"])
            if len(dataset["file_names"]) == 0:
                return False
        else:
            return False

    return True


def create_dataset(audio_dir, annotation_dir):
    """Creates a new dataset. Loads annotations if they exist, otherwise creates new ones.

    This will be replaced by a database lookup.

    :param audio_dir (string):
    :param annotation_dir (string):
    :return: dataset ID
    """

    for dd in datasets:
        if audio_dir == datasets[dd]["audio_dir"]:
            # dataset already exist so don't need to create it again
            # TODO might want to have option to reload a dataset
            return datasets[dd]["id"]

    # load the paths - exit if no audio files
    audio_files = list(Path(audio_dir).rglob("*.wav")) + list(
        Path(audio_dir).rglob("*.WAV")
    )
    audio_files = [os.path.join(aa.parent, aa.name) for aa in audio_files]
    if len(audio_files) == 0:
        return "none"

    # create paths for annotation files
    ann_file_paths = [
        aa.replace(audio_dir, annotation_dir) + ".json" for aa in audio_files
    ]
    class_names = []
    event_names = []
    annotations = {}

    # load or create annotations
    for ann_path in ann_file_paths:
        ann_path_short = ann_path[len(annotation_dir) :]
        if os.path.isfile(ann_path):
            try:
                with open(ann_path) as da:
                    data = json.load(da)
                data["file_name"] = ann_path_short
                data["hash_id"] = hash_str(data["file_name"])

                # load class names etc if there are any
                if data["class_name"] != "":
                    class_names.append(data["class_name"])
                for aa in data["annotation"]:
                    class_names.append(aa["class"])
                    event_names.append(aa["event"])
            except:
                print("Error loading: " + ann_path_short)
                data = create_blank_annotation_file(ann_path_short)
        else:
            # create new annotation
            data = create_blank_annotation_file(ann_path_short)

        # store the loaded annotation
        # TODO would be much better to use a hash of file_name as the key i.e. ['hash_id']
        annotations[data["file_name"]] = data

    # create new dataset
    dataset = {}
    dataset["id"] = hash_str(audio_dir)
    dataset["audio_dir"] = audio_dir
    dataset["annotation_dir"] = annotation_dir
    dataset["annotations"] = annotations
    dataset["file_names"] = sorted(list(annotations.keys()))

    # ensure the ordering from config is preserved
    dataset["event_names"] = config.EVENT_NAMES + sorted(
        list(set(event_names) - set(config.EVENT_NAMES))
    )
    dataset["class_names"] = config.CLASS_NAMES + sorted(
        list(set(class_names) - set(config.CLASS_NAMES))
    )

    # add to global datasets dictionary
    datasets[dataset["id"]] = dataset

    return dataset["id"]


if __name__ == "__main__":

    # application.run(host='127.0.0.1', port=8000, debug=True, use_reloader=True)
    application.run(host="127.0.0.1", port=8000)
