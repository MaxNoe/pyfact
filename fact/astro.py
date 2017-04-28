from astropy.coordinates import EarthLocation, AltAz, get_sun
import astropy.units as u
from astropy.time import Time
import numpy as np
from scipy.interpolate import UnivariateSpline


sun_angle_of_period = {
    'dark_time': -18,
    'astronomical_twilight': -12,
    'nautical_twilight': -6,
    'civil_twilight': 0,
}


fact_location = EarthLocation.from_geodetic(
    lon='-17d53m28.00s',
    lat='28d45m41.88s',
    height=2195*u.meter,
)


def calc_sun_altitude(times):

    sun = get_sun(times)
    altaz = AltAz(location=fact_location, obstime=times)
    altitude = sun.transform_to(altaz).alt.deg

    return altitude


def calc_start_of(period, day):
    '''
    Calculate the start of astronomical periods for a given day

    Parameter
    ---------

    period: str
        - any of: dark_time, astronomical_twilight, nautical_twilight, civil_twilight
    day: str or datetime object or astropy.time.Time
    '''
    assert period in sun_angle_of_period

    t = Time(Time(day).datetime.replace(hour=15, minute=0))
    times = t + np.linspace(0, 12, 50) * u.hour

    alt = calc_sun_altitude(times)
    spl = UnivariateSpline(times.unix, alt - sun_angle_of_period[period])

    twilight = spl.roots()[0]

    return Time(twilight, format='unix').utc.to_datetime()


def calc_end_of(period, day):
    '''
    Calculate the end of astronomical periods for a given day

    Parameter
    ---------

    period: str
        - any of: dark_time, astronomical_twilight, nautical_twilight, civil_twilight
    day: str or datetime object or astropy.time.Time
    '''
    assert period in sun_angle_of_period

    t = Time(Time(day).datetime.replace(hour=2, minute=0))
    times = t + np.linspace(0, 12, 50) * u.hour

    alt = calc_sun_altitude(times)
    spl = UnivariateSpline(times.unix, alt - sun_angle_of_period[period])

    twilight = spl.roots()[0]

    return Time(twilight, format='unix').utc.to_datetime()
