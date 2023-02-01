# Data Format

Recording and annotation data are stored in a JSON format. Each recording info
with its corresponding annotations are stored in a separate file, with the file 
name corresponding to the recording ID and suffixed with `.json`.

## Recording Info

The recording info is stored in the top-level of the JSON file. The following
fields are included:

- `id`: The recording ID, which is the file name (with the `.wav` suffix).
- `duration`: The duration of the recording in seconds.
- `class_name`: A field to store a file level class name.
- `time_exp`: The time expansion factor used to generate the recording. If not
  specified, the default value is 1.
- `annotated`: A boolean field (true/false) to indicate whether the recording
  has been fully annotated.
- `issues`: A boolean field (true/false) to flag any issues with the recording.
  This is used to indicate that the recording or annotations should be reviewed.
- `notes`: A field to store any notes about the recording.
- `annotation`: A list of annotations for the recording.

## Annotation

Annotations are made in the form of bounding boxes. Each annotation is stored as
a dictionary with the following fields:

- `class`: The class name associated to the annotation.
- `start_time`: The start time of the annotation in seconds.
- `end_time`: The end time of the annotation in seconds.
- `individual`: The individual ID associated to the annotation.
- `event`: The event type associated to the annotation.
- `low_freq`: The low frequency of the annotation in Hz.
- `high_freq`: The high frequency of the annotation in Hz.

## Example

```json
{
  "id": "20170701_213954-MYOMYS-LR_0_0.5.wav",
  "duration": 0.5,
  "class_name": "Myotis mystacinus",
  "annotated": true,
  "issues": false,
  "notes": "",
  "time_exp": 1,
  "annotation": [
    {
      "class": "Myotis mystacinus",
      "end_time": 0.151696,
      "event": "Echolocation",
      "high_freq": 105957.03125,
      "individual": "0",
      "low_freq": 28564.453125,
      "start_time": 0.146366
    },
    {
      "class": "Myotis mystacinus",
      "end_time": 0.028696,
      "event": "Echolocation",
      "high_freq": 95214.84375,
      "individual": "0",
      "low_freq": 34667.96875,
      "start_time": 0.025006
    },
    {
      "class": "Myotis mystacinus",
      "end_time": 0.059036,
      "event": "Echolocation",
      "high_freq": 107910.15625,
      "individual": "0",
      "low_freq": 30517.578125,
      "start_time": 0.053296
    }
  ]
}
```
