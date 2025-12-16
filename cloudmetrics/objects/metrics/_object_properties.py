import numpy as np
from skimage.measure import regionprops


# Compute regionprops for every image, for every metric, that is passed.
def _get_regionprops(object_labels):
    return regionprops(label_image=object_labels)


def _get_objects_property(object_labels, property_name):
    regions = _get_regionprops(object_labels=object_labels)
    values = [getattr(region, property_name) for region in regions]
    return np.asarray(values)


def _get_objects_area(object_labels):
    return _get_objects_property(object_labels=object_labels, property_name="area")
