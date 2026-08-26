# AI Tracking Module

The detection/tracking pipeline lives in its own repository rather than being duplicated here, since it's reused across a few different vision projects.

Repository: https://github.com/nistordarius26h-ship-it/ai_multiobject_python_tracker

**Features**
- Real-time detection with Ultralytics YOLO
- Multi-object tracking with ByteTrack
- Person-following mode for the robot
- CUDA/ROCm GPU acceleration, CPU fallback
- Motion trails, speed estimation, telemetry overlay
- Works with webcams, RTSP, drones, and other live sources

See [`docs/6)ai-tracking-computer-vision.md`](./docs/6%29ai-tracking-computer-vision.md) for how it's adapted to the robot.
