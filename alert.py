import pygame


class Alarm:
    """
    Simple looping alarm sound. If the sound file can't be loaded
    (e.g. missing assets/alarm.wav during a hackathon demo), the alarm
    silently disables itself instead of crashing the whole app -- the
    on-screen STATUS text still works as the visual alert.
    """

    def __init__(self, sound_file):
        self.enabled = True
        self.playing = False

        try:
            pygame.mixer.init()
            self.sound = pygame.mixer.Sound(sound_file)
        except Exception as e:
            print(f"[Alarm] Warning: could not load '{sound_file}' ({e}). "
                  f"Audio alarm disabled, visual alert will still work.")
            self.enabled = False
            self.sound = None

    def start(self):
        if self.enabled and not self.playing:
            self.sound.play(-1)  # Loop forever
            self.playing = True

    def stop(self):
        if self.enabled and self.playing:
            self.sound.stop()
            self.playing = False
