import subprocess
import os

FFMPEG = "/Users/pavan/.local/bin/ffmpeg"

segments = [
    {
        "name": "seg1_interior",
        "input": "scratch_videos/vid_29050.mp4",
        "ss": "00:00:00.5",
        "t": "3.5",
        "vf": "scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,fps=25,format=yuv420p"
    },
    {
        "name": "seg2_dining",
        "input": "scratch_videos/4385.mp4",
        "ss": "00:00:02.0",
        "t": "3.5",
        "vf": "scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,fps=25,format=yuv420p"
    },
    {
        "name": "seg3_friends",
        "input": "scratch_videos/43248.mp4",
        "ss": "00:00:01.0",
        "t": "3.5",
        "vf": "scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,fps=25,format=yuv420p"
    },
    {
        "name": "seg4_dosa",
        "input": "scratch_videos/dosa_crispy.webm",
        "ss": "00:00:00.0",
        "t": "2.8",
        "vf": "crop=1080:1080:0:700,scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,fps=25,format=yuv420p"
    },
    {
        "name": "seg5_service",
        "input": "scratch_videos/219.mp4",
        "ss": "00:00:00.0",
        "t": "3.5",
        "vf": "scale=-1:960,crop=1080:960:0:0,fps=25,format=yuv420p"
    },
    {
        "name": "seg6_steaming_tea",
        "input": "scratch_videos/9267.mp4",
        "ss": "00:00:01.0",
        "t": "3.5",
        "vf": "scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,fps=25,format=yuv420p"
    }
]

# 1. Process each segment
seg_files = []
for i, s in enumerate(segments):
    out_file = f"scratch_videos/{s['name']}.mp4"
    cmd = [
        FFMPEG, "-y",
        "-ss", s["ss"],
        "-i", s["input"],
        "-t", s["t"],
        "-vf", s["vf"],
        "-an",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        out_file
    ]
    print(f"Rendering segment {i+1}/{len(segments)}: {s['name']}...")
    subprocess.run(cmd, check=True)
    seg_files.append(out_file)

print("All segments rendered. Joining with xfade...")

# Calculate xfade offsets
# Each xfade transition has duration 0.5s
# dur1 = 3.5 -> offset1 = 3.5 - 0.5 = 3.0
# dur2 = 3.5 -> offset2 = 3.0 + 3.5 - 0.5 = 6.0
# dur3 = 3.5 -> offset3 = 6.0 + 3.5 - 0.5 = 9.0
# dur4 = 2.8 -> offset4 = 9.0 + 2.8 - 0.5 = 11.3
# dur5 = 3.5 -> offset5 = 11.3 + 3.5 - 0.5 = 14.3
# dur6 = 3.5 -> final duration = 14.3 + 3.5 = 17.8s

# Build filter_complex string
inputs = []
for f in seg_files:
    inputs.extend(["-i", f])

filter_str = (
    "[0:v][1:v]xfade=transition=fade:duration=0.5:offset=3.0[v01];"
    "[v01][2:v]xfade=transition=fade:duration=0.5:offset=6.0[v02];"
    "[v02][3:v]xfade=transition=fade:duration=0.5:offset=9.0[v03];"
    "[v03][4:v]xfade=transition=fade:duration=0.5:offset=11.3[v04];"
    "[v04][5:v]xfade=transition=fade:duration=0.5:offset=14.3[outv]"
)

out_final = "scratch_videos/restaurant_ambience.mp4"
cmd_join = [
    FFMPEG, "-y",
    *inputs,
    "-filter_complex", filter_str,
    "-map", "[outv]",
    "-c:v", "libx264",
    "-preset", "slow",
    "-crf", "20",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    out_final
]

subprocess.run(cmd_join, check=True)
print(f"Ambience video successfully created: {out_final}")
