import cv2
from pathlib import Path
from tempfile import NamedTemporaryFile


class CrowdDetectionService:
    def __init__(self):
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect_people(self, image_file):
        image_path = self._save_temp_file(image_file)
        try:
            count = self.detect_people_from_path(image_path)
        finally:
            Path(image_path).unlink(missing_ok=True)
        return count

    def detect_people_from_path(self, path):
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError('Unable to load uploaded image.')

        rects, weights = self.hog.detectMultiScale(
            image,
            winStride=(8, 8),
            padding=(16, 16),
            scale=1.05
        )

        return len(rects)

    def get_crowd_status(self, people_count):
        if people_count < 5:
            return 'Low'
        if people_count <= 12:
            return 'Moderate'
        return 'Crowded'

    def _save_temp_file(self, uploaded_file):
        if hasattr(uploaded_file, 'temporary_file_path'):
            return uploaded_file.temporary_file_path()

        suffix = Path(getattr(uploaded_file, 'name', 'image')).suffix or '.jpg'
        with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            return temp_file.name
