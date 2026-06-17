import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import tkinter as tk

recording = False
audio_frames = []
stream = None


def start_recording(event=None):
    global recording
    global audio_frames
    global stream

    if recording:
        return

    print("Started Recording")

    recording = True
    audio_frames = []

    def callback(indata, frames, time, status):
        if recording:
            audio_frames.append(indata.copy())

    stream = sd.InputStream(
        samplerate=16000,
        channels=1,
        callback=callback
    )

    stream.start()


def stop_recording(event=None):
    global recording
    global stream

    if not recording:
        return

    print("Stopped Recording")

    recording = False

    stream.stop()
    stream.close()

    if len(audio_frames) == 0:
        print("No audio recorded")
        return

    audio = np.concatenate(
        audio_frames,
        axis=0
    )

    write(
        "voice.wav",
        16000,
        audio
    )

    print("Saved voice.wav")


root = tk.Tk()

root.geometry("400x200")
root.title("Voice Test")

label = tk.Label(
    root,
    text="Hold LEFT OPTION to record"
)

label.pack(expand=True)

root.bind(
    "<KeyPress-Alt_L>",
    start_recording
)

root.bind(
    "<KeyRelease-Alt_L>",
    stop_recording
)

root.mainloop()