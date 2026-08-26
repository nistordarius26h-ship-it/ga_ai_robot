# AI Tracking: YOLO11 + ByteTrack + OpenCV

Real-time detection-and-tracking pipeline for autonomous target-following. Runs offboard on a GPU workstation, not on the robot. Originally built and tested on DJI Mini 3 drone footage before being adapted to person-following. Source: [`ai_multiobject_python_tracker`](https://github.com/nistordarius26h-ship-it/ai_multiobject_python_tracker).

## Why offboard

YOLO11x (the extra-large variant, chosen for accuracy) needs a real GPU. Inference runs on a separate workstation; the Pi only handles video capture/streaming and motor control. Onboard inference is future work, once a smaller model's latency/accuracy tradeoff is acceptable.

## Pipeline

```
Live video source (drone / RTSP / webcam / YouTube Live)
        │  streamlink resolves the media URL
        ▼
OpenCV VideoCapture — background thread into a queue
        ▼
YOLO11 detection (Ultralytics)
        ▼
ByteTrack (tracker="bytetrack.yaml")
        ▼
Kinematics — speed estimation, motion trails, occlusion grace period
        ▼
Annotated video output (cv2.imshow, or redirected to a stream)
```

## Detection: YOLO11

- Model: `yolo11x.pt` (Ultralytics), largest variant — inference runs on a dedicated GPU, so this prioritizes accuracy.
- Class filter: `target = [0, 2, 3, 5, 7, 16, 18]` (person, car, motorcycle, bus, truck, dog, horse) — cuts false positives for a person-following use case.
- Confidence threshold: `0.40`.
- GPU detection: checks `torch.cuda.is_available()`, distinguishes NVIDIA CUDA vs. AMD ROCm (`torch.version.hip`), falls back to CPU. Development GPU is an AMD RX 7800 XT, where ROCm/HIP needs more manual setup than CUDA.

## Tracking: ByteTrack

`model.track(..., tracker="bytetrack.yaml", persist=True)`. Chosen over centroid tracking because it keeps low-confidence detections associated with existing tracks instead of dropping them — fewer ID switches during brief occlusion or a confidence dip.

## Kinematics / visualization

- Motion trails: per-track `deque` (max 40 points), drawn as connected segments.
- Speed estimate: pixel displacement between frames, scaled by a configurable `mpp` (meters-per-pixel) constant, smoothed (`smoothing = 0.85`). Rough approximation — accurate speed needs real mpp calibration for the specific camera height/angle.
- Occlusion handling: track stays drawn for `grace = 0.5s` after last detection, removed after `timeout = 2.0s`. Prevents flicker on missed frames without letting stale tracks linger.
- On-screen: device, smoothed FPS, active track count, runtime, per-class counts.

## Threaded capture

`queuestream` class: background thread reads `cv2.VideoCapture` into a bounded `queue.Queue` (60 frames); main loop pulls and runs inference. Decouples the (often slower) stream read from the detection loop, pre-buffers ~15 frames to smooth early jitter.

## Frame pacing

Measures actual source FPS (`cv2.CAP_PROP_FPS`, falls back to 30 if invalid), sleeps out remaining time per iteration so playback stays paced to the source rate instead of burning through the buffer.

## Dependencies

```
torch>=2.7.0
torchvision>=0.22.0
ultralytics>=8.3.0
opencv-python>=4.10.0
numpy>=2.0.0
streamlink>=7.0.0
PyYAML>=6.0
```

GPU-specific PyTorch (CUDA or ROCm) installs separately per the [PyTorch install guide](https://pytorch.org/get-started/locally/) — not pulled by `requirements.txt`, since the right build depends on the host GPU vendor.

## Adapting to the robot

Same `tracker.py` pipeline, pointed at the robot's WebRTC/MediaMTX stream instead of a drone or YouTube URL (see [`4)raspberry-pi-setup.md`](./4%29raspberry-pi-setup.md), [`5)cloudflare-telegram-remote-access.md`](./5%29cloudflare-telegram-remote-access.md)). Target-follow logic converts the tracked box's position/size into steering commands sent back over the same control channel the joystick UI uses.
