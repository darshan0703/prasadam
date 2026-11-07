import subprocess
import os

FFMPEG = "/Users/pavan/.local/bin/ffmpeg"

scenes = [
    {
        "name": "scene1_hero_couple",
        "input": "frontend/public/prasadam_hero.jpg",
        "dur": "4.0",
        # Subtle slow zoom in centered on the dining table and background couple, with gentle diya flicker
        "vf": (
            "scale='1080*(1+0.035*t)':'960*(1+0.035*t)':eval=frame,"
            "crop=1080:960:'(in_w-out_w)/2':'(in_h-out_h)/2',"
            "eq=brightness='0.012*sin(2*PI*t/1.8)':saturation=1.05,"
            "fps=25,format=yuv420p"
        )
    },
    {
        "name": "scene2_south_tiffin",
        "input": "frontend/public/category_south_indian.jpg",
        "dur": "4.0",
        # Cinematic pan across the golden dosa, idli, medu vada, and drumstick sambar on banana leaf
        "vf": (
            "scale='-1:960*(1+0.02*t)':eval=frame,"
            "crop=1080:960:'(in_w-out_w)*(t/4.0)':'(in_h-out_h)/2',"
            "eq=brightness='0.008*sin(2*PI*t/2.0)':saturation=1.04,"
            "fps=25,format=yuv420p"
        )
    },
    {
        "name": "scene3_banana_leaf_meals",
        "input": "frontend/public/category_meals_rice.jpg",
        "dur": "4.0",
        # Gentle slow push-in over the banana leaf thali with rice, ghee, sambar, rasam, palya, and papad
        "vf": (
            "scale='-1:960*(1+0.03*t)':eval=frame,"
            "crop=1080:960:'(in_w-out_w)/2':'(in_h-out_h)*(0.3+0.2*t/4.0)',"
            "eq=saturation=1.03,"
            "fps=25,format=yuv420p"
        )
    },
    {
        "name": "scene4_ghee_roast_dosa",
        "input": "frontend/public/menu-items/ghee_roast_masala_dosa.jpg",
        "dur": "4.0",
        # Slow pan and push-in on the glistening ghee dosa crust, potato masala filling, and chutneys
        "vf": (
            "scale='-1:960*(1+0.03*t)':eval=frame,"
            "crop=1080:960:'(in_w-out_w)*(0.2+0.6*t/4.0)':'(in_h-out_h)/2',"
            "eq=brightness='0.01*sin(2*PI*t/2.2)':saturation=1.05,"
            "fps=25,format=yuv420p"
        )
    },
    {
        "name": "scene5_filter_coffee_heritage",
        "input": "frontend/public/category_beverages_sweets.jpg",
        "dur": "4.0",
        # Slow glide across the brass dabarah filter kaapi, mysore pak, and South Indian patrons in background
        "vf": (
            "scale='-1:960*(1+0.025*t)':eval=frame,"
            "crop=1080:960:'(in_w-out_w)*(1.0-t/4.0)':'(in_h-out_h)/2',"
            "eq=brightness='0.012*sin(2*PI*t/1.9)':saturation=1.05,"
            "fps=25,format=yuv420p"
        )
    }
]

# 1. Render each scene
rendered_files = []
for i, s in enumerate(scenes):
    out_file = f"scratch_videos/{s['name']}.mp4"
    cmd = [
        FFMPEG, "-y",
        "-loop", "1",
        "-i", s["input"],
        "-t", s["dur"],
        "-vf", s["vf"],
        "-an",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        out_file
    ]
    print(f"Rendering scene {i+1}/{len(scenes)}: {s['name']}...")
    subprocess.run(cmd, check=True)
    rendered_files.append(out_file)

print("All scenes rendered. Joining with seamless xfade cross-dissolves...")

# 5 scenes, each 4.0s duration, transition duration 0.6s
# offset1 = 4.0 - 0.6 = 3.4
# offset2 = 3.4 + 4.0 - 0.6 = 6.8
# offset3 = 6.8 + 4.0 - 0.6 = 10.2
# offset4 = 10.2 + 4.0 - 0.6 = 13.6
# final duration = 13.6 + 4.0 = 17.6s

inputs = []
for f in rendered_files:
    inputs.extend(["-i", f])

filter_str = (
    "[0:v][1:v]xfade=transition=fade:duration=0.6:offset=3.4[v01];"
    "[v01][2:v]xfade=transition=fade:duration=0.6:offset=6.8[v02];"
    "[v02][3:v]xfade=transition=fade:duration=0.6:offset=10.2[v03];"
    "[v03][4:v]xfade=transition=fade:duration=0.6:offset=13.6[outv]"
)

out_master = "scratch_videos/prasadam_ambience_master.mp4"
cmd_join = [
    FFMPEG, "-y",
    *inputs,
    "-filter_complex", filter_str,
    "-map", "[outv]",
    "-c:v", "libx264",
    "-preset", "slow",
    "-crf", "22",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    out_master
]
subprocess.run(cmd_join, check=True)
print(f"Master ambience video created: {out_master}")

# Copy directly to frontend/public/videos/restaurant_ambience.mp4
dest = "frontend/public/videos/restaurant_ambience.mp4"
os.makedirs("frontend/public/videos", exist_ok=True)
subprocess.run(["cp", out_master, dest], check=True)
print(f"Copied to public asset directory: {dest}")
