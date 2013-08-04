
from django.core.files import File
import random
import os
from django.conf import settings


def get_random_image():
    samples = os.path.realpath(os.path.join(settings.PROJECT_PATH,"../sample"))
    files = os.listdir(samples)
    filename = random.choice(files)
    filepath = os.path.join(samples,filename)
    return filename,File(open(filepath))
