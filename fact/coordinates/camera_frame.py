from astropy.coordinates import (
    BaseCoordinateFrame,
    AltAz,
    frame_transform_graph,
    FunctionTransform,
)

from astropy.coordinates import (
    CoordinateAttribute,
    TimeAttribute,
    EarthLocationAttribute,
    Attribute
)

from astropy.coordinates.matrix_utilities import rotation_matrix
from astropy.coordinates.representation import CartesianRepresentation
import astropy.units as u

from .representation import PlanarRepresentation
from ..instrument.constants import FOCAL_LENGTH_MM, LOCATION
import numpy as np


class CameraFrame(BaseCoordinateFrame):
    '''
    Astropy CoordinateFrame representing coordinates in the CameraPlane

    Attributes
    ----------
    pointing_direction: astropy.coordinates.AltAz
        The pointing direction of the telescope
    obstime: astropy.Time
        The timestamp of the observation, only needed to directly transform
        to Equatorial coordinates, transforming to AltAz does not need this.
    location: astropy.coordinates.EarthLocation
        The location of the observer,  only needed to directly transform
        to Equatorial coordinates, transforming to AltAz does not need this,
        default is FACT's location
    rotated: bool
        True means x points right and y points up when looking on the camera
        from the dish, which is the efinition of FACT-Tools >= 1.0 and Mars.
        False means x points up and y points left,
        which is definition in the original FACTPixelMap file.
    '''
    default_representation = PlanarRepresentation
    pointing_direction = CoordinateAttribute(frame=AltAz, default=None)
    obstime = TimeAttribute(default=None)
    location = EarthLocationAttribute(default=LOCATION)
    rotated = Attribute(default=True)
    focal_length = Attribute(default=FOCAL_LENGTH_MM * u.mm)


@frame_transform_graph.transform(FunctionTransform, CameraFrame, AltAz)
def camera_to_altaz(camera, altaz):
    if camera.pointing_direction is None:
        raise ValueError('Pointing Direction must not be None')

    x = camera.x.copy()
    y = camera.y.copy()

    if camera.rotated is True:
        x, y = y, -x

    focal_length = camera.focal_length
    z = 1 / np.sqrt(1 + (x / focal_length)**2 + (y / focal_length)**2)
    x *= z / focal_length
    y *= z / focal_length

    cartesian = CartesianRepresentation(x, y, z, copy=False)

    rot_z_az = rotation_matrix(-camera.pointing_direction.az, 'z')
    rot_y_zd = rotation_matrix(-camera.pointing_direction.zen, 'y')

    cartesian = cartesian.transform(rot_y_zd)
    cartesian = cartesian.transform(rot_z_az)

    altitude = 90 * u.deg - np.arccos(cartesian.z)
    azimuth = np.arctan2(cartesian.y, cartesian.x)

    return AltAz(
        alt=altitude,
        az=azimuth,
        location=camera.location,
        obstime=camera.obstime,
    )


@frame_transform_graph.transform(FunctionTransform, AltAz, CameraFrame)
def altaz_to_camera(altaz, camera):
    if camera.pointing_direction is None:
        raise ValueError('Pointing Direction must not be None')

    cartesian = altaz.cartesian

    rot_z_az = rotation_matrix(camera.pointing_direction.az, 'z')
    rot_y_zd = rotation_matrix(camera.pointing_direction.zen, 'y')

    cartesian = cartesian.transform(rot_z_az)
    cartesian = cartesian.transform(rot_y_zd)

    focal_length = camera.focal_length
    x = (cartesian.x * focal_length / cartesian.z).copy()
    y = (cartesian.y * focal_length / cartesian.z).copy()

    if camera.rotated is True:
        x, y = -y, x

    return CameraFrame(
        x=x,
        y=y,
        pointing_direction=camera.pointing_direction,
        obstime=altaz.obstime,
        location=camera.location,
    )
