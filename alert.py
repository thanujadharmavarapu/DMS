import pygame


class Alarm:
    def __init__(self, sound_file):
        pygame.mixer.init()
        self.sound = pygame.mixer.Sound(sound_file)
        self.playing = False

    def start(self):
        if not self.playing:
            self.sound.play(-1)  # Loop forever
            self.playing = True

    def stop(self):
        if self.playing:
            self.sound.stop()
            self.playing = False