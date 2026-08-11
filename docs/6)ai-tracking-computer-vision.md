# AI Tracking: YOLO11 + ByteTrack + OpenCV

The robot's autonomous target-following relies on a real-time detection-and-tracking pipeline. The pipeline runs **offboard** (on a GPU workstation, not on the robot itself) and was originally built and validated on live footage from a **DJI Mini 3 drone** before being adapted to the robot's person-following use case. Source: [`ai_multiobject_python_tracker`](https://github.com/nistordarius26h-ship-it/ai_multiobject_python_tracker).

## Why offboard inference

Running YOLO11x — the extra-large variant, chosen for accuracy over speed — needs a real GPU. Rather than compromise on model size to fit an edge device, inference runs on a separate GPU workstation and the Raspberry Pi only handles video capture/streaming and motor control. Onboard (edge) inference is listed as future work once latency/accuracy tradeoffs with a smaller model are acceptable.

## Pipeline architecture

```
Live video source (drone / RTSP / webcam / YouTube Live)
        │  (streamlink resolves the actual media URL)
        ▼
OpenCV VideoCapture — pulled on a background thread into a queue
        ▼
YOLO11 detection (Ultralytics)
        ▼
ByteTrack (multi-object tracker, tracker="bytetrack.yaml")
        ▼
Kinematics engine — speed estimation, motion trails, occlusion grace period
        ▼
Annotated video output (cv2.imshow / can be redirected to a stream)
```

## Detection: YOLO11

- Model: `yolo11x.pt` (Ultralytics), the largest YOLO11 variant — prioritizes accuracy since inference happens on a dedicated GPU, not an edge device.
- Class filtering: only a subset of COCO classes is tracked (`target = [0, 2, 3, 5, 7, 16, 18]` — person, car, motorcycle, bus, truck, dog, horse), which cuts down false positives and rendering clutter for a person-following/monitoring use case.
- Confidence threshold: `0.40` — tuned to balance missed detections against noisy low-confidence boxes.
- GPU auto-detection: the script checks `torch.cuda.is_available()` and further distinguishes NVIDIA CUDA vs. AMD ROCm (`torch.version.hip`), falling back to CPU automatically if no GPU is usable. This was necessary because development happened on an **AMD Radeon RX 7800 XT**, where ROCm/HIP PyTorch builds require more manual setup than CUDA.

## Tracking: ByteTrack

`model.track(..., tracker="bytetrack.yaml", persist=True)` — ByteTrack is used instead of a simpler tracker (e.g. centroid tracking) because it also associates *low-confidence* detections with existing tracks instead of discarding them, which meaningfully reduces ID switches when a target is briefly occluded or a detection dips below the confidence threshold for a frame or two.

## Kinematics & visualization layer

Built on top of the raw tracker output:

- **Motion trails** — a per-track `deque` (max length 40) of center points, drawn as connected line segments, giving a visual path history for each tracked object.
- **Speed estimation** — computed from pixel displacement between frames, converted with a configurable `mpp` (meters-per-pixel) calibration constant, exponentially smoothed (`smoothing = 0.85`) to avoid frame-to-frame jitter in the displayed km/h value. This is a rough approximation, not a calibrated measurement — accurate speed requires a proper meters-per-pixel calibration for the specific camera height/angle in use.
- **Occlusion handling / grace period** — a track is still drawn for `grace = 0.5s` after its last detection, and only fully removed after `timeout = 2.0s` of no detections. This prevents bounding-box flicker when YOLO misses a detection for a frame or two, without letting stale tracks linger indefinitely.
- **On-screen telemetry** — device in use, live FPS (smoothed), count of currently tracked objects, runtime, and a per-class object count overlay.

## Threaded frame capture

Video I/O is decoupled from inference using a small `queuestream` class: a background thread continuously reads frames from `cv2.VideoCapture` into a bounded `queue.Queue` (60 frames), while the main loop pulls from that queue and runs inference. This prevents the (often slower) network/stream read from blocking or throttling the detection loop, and lets the pipeline pre-buffer ~15 frames before starting to smooth out early stream jitter.

## Frame-rate pacing

The loop measures the actual source stream FPS (`cv2.CAP_PROP_FPS`, with a sane fallback to 30 if the reported value is invalid) and sleeps out any remaining time each iteration so playback/processing stays paced to the source's real frame rate rather than running as fast as possible and burning through the buffer.

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

GPU-specific PyTorch (CUDA or ROCm build) must be installed separately per the [official PyTorch install guide](https://pytorch.org/get-started/locally/) — it is not pulled automatically by `requirements.txt` since the correct build depends entirely on the host's GPU vendor.

## Adapting this for the robot

For the robot's person-following mode, the same `tracker.py` pipeline is pointed at the robot's own onboard camera feed (via the WebRTC/MediaMTX stream from the Raspberry Pi, see [`raspberry-pi-setup.md`](./raspberry-pi-setup.md) and [`cloudflare-telegram-remote-access.md`](./cloudflare-telegram-remote-access.md)) instead of a drone or YouTube Live URL, with the target-follow logic converting the tracked bounding box's position/size into steering commands sent back to the Pi over the same control channel the joystick UI uses.
