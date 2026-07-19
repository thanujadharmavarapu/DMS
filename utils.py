import cv2
import math


def euclidean_distance(point1, point2):
    """
    Calculate Euclidean distance between two points.
    """
    x1, y1 = point1
    x2, y2 = point2

    distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    return distance


def draw_text(frame, text, position,
              color=(0, 255, 0),
              scale=0.8,
              thickness=2):

    cv2.putText(
        frame,
        text,
        position,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        thickness
    )


def draw_circle(frame, point,
                 color=(0, 255, 0),
                 radius=2):

    cv2.circle(
        frame,
        point,
        radius,
        color,
        -1
    )


def draw_status_panel(frame, lines, origin=(20, 40), line_gap=40,
                       scale=0.8, thickness=2):
    """
    Draws a clean, minimal stack of text lines.
    `lines` is a list of (text, color) tuples, drawn top to bottom.
    Used to keep the on-screen UI limited to exactly what's required
    (EAR, Head Position, STATUS) with nothing extra.
    """

    x, y = origin

    for text, color in lines:
        draw_text(frame, text, (x, y), color=color, scale=scale, thickness=thickness)
        y += line_gap