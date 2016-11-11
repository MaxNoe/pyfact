from .base import AuxService
import pandas as pd


def fact_mjd_to_datetime(fact_mjd):
    ''' convert fact mjds (days since unix epoch) to pandas datetimes '''
    return pd.to_datetime(fact_mjd * 24 * 3600 * 1e9)


__all__ = [
    'MagicWeather',
    'PfMini',
    'DriveTracking',
    'DrivePointing',
    'DriveSource',
    'FSCHumidity',
    'FSCTemperature',
    'FTMTriggerRates',
    'BiasVoltage',
    'FADTemperature',
    'BiasCurrentUncalibrated',
    'BiasCurrentCalibrated',
    'TriggerThresholds',
]


class MagicWeather(AuxService):
    basename = 'MAGIC_WEATHER_DATA'
    renames = {
        'Time': 'timestamp',
        'T': 'temperature',
        'T_dew': 'dewpoint',
        'H': 'humidity',
        'P': 'pressure',
        'v': 'wind_speed',
        'v_max': 'wind_gust_speed',
        'd': 'wind_direction',
    }

    ignored_columns = ['stat', 'QoS']
    transforms = {'timestamp': fact_mjd_to_datetime}


class PfMini(AuxService):
    basename = 'PFMINI_CONTROL_DATA'
    renames = {
        'Time': 'timestamp',
        'Temperature': 'temperature',
        'Humidity': 'humidity',
    }

    ignored_columns = ['QoS', ]
    transforms = {'timestamp': fact_mjd_to_datetime}


class DriveTracking(AuxService):
    basename = 'DRIVE_CONTROL_TRACKING_POSITION'
    renames = {
        'Time': 'timestamp',
        'Ra': 'right_ascension',
        'Dec': 'declination',
        'Ha': 'hourangle',
        'SrcHa': 'hourangle_source',
        'SrcRa': 'right_ascension_source',
        'SrcDec': 'declination_source',
        'HaDec': 'hourangle_source',
        'Zd': 'zenith',
        'Az': 'azimuth',
        'dZd': 'zenith_deviation',
        'dAz': 'azimuth_deviation',
        'dev': 'absolute_control_deviation',
        'avgdev': 'average_control_deviation',
    }
    transforms = {'timestamp': fact_mjd_to_datetime}
    ignored_columns = ['QoS', ]


class DrivePointing(AuxService):
    basename = 'DRIVE_CONTROL_POINTING_POSITION'
    renames = {
        'Time': 'timestamp',
        'Zd': 'zenith',
        'Az': 'azimuth',
    }
    transforms = {'timestamp': fact_mjd_to_datetime}
    ignored_columns = ['QoS', ]


class DriveSource(AuxService):
    basename = 'DRIVE_CONTROL_SOURCE_POSITION'
    renames = {
        'Time': 'timestamp',
        'Ra_src': 'right_ascension_source',
        'Ra_cmd': 'right_ascension_command',
        'Dec_src': 'declination_source',
        'Dec_cmd': 'declination_command',
        'Offset': 'wobble_offset',
        'Angle': 'wobble_angle',
        'Name': 'source_name',
        'Period': 'orbit_period',
    }
    transforms = {'timestamp': fact_mjd_to_datetime}
    ignored_columns = ['QoS', ]


class FSCHumidity(AuxService):
    basename = 'FSC_CONTROL_HUMIDITY'
    renames = {
        'Time': 'timestamp',
        't': 'fsc_uptime',
        'H': 'humidity',
    }
    transforms = {'timestamp': fact_mjd_to_datetime}
    ignored_columns = ['QoS', ]


class FSCTemperature(AuxService):
    basename = 'FSC_CONTROL_TEMPERATURE'
    renames = {
        'Time': 'timestamp',
        't': 'fsc_uptime',
        'T_crate': 'crate_temperature',
        'T_sens': 'sensor_compartment_temperature',
        'T_ps': 'power_supply_temperature',
        'T_aux': 'auxiliary_power_supply_temperature',
        'T_back': 'ftm_backpanel_temperature',
        'T_eth': 'ethernet_temperature',
    }
    transforms = {'timestamp': fact_mjd_to_datetime}
    ignored_columns = ['QoS', ]


class FTMTriggerRates(AuxService):
    basename = 'FTM_CONTROL_TRIGGER_RATES'
    renames = {
        'Time': 'timestamp',
        'FTMtimeStamp': 'ftm_timestamp',
        'OnTimeCounter': 'effective_ontime',
        'TriggerCounter': 'trigger_counter',
        'TriggerRate': 'trigger_rate',
        'BoardRate': 'board_rate',
        'PatchRate': 'patch_rate',
        'OnTime': 'ontime',
        'ElapsedTime': 'elapsed_time',
    }
    transforms = {
        'timestamp': fact_mjd_to_datetime,
        'ftm_timestamp': lambda x: x/1e6,
        'effective_ontime': lambda x: x/1e6,
    }
    ignored_columns = ['QoS', ]


class BiasVoltage(AuxService):
    basename = "BIAS_CONTROL_VOLTAGE"
    renames = {
        'Time': 'timestamp',
        'Uout': 'bias_voltage',
    }
    transforms = {
        'timestamp': fact_mjd_to_datetime,
    }
    ignored_columns = ['QoS', ]


class FADTemperature(AuxService):
    basename = "FAD_CONTROL_TEMPERATURE"
    renames = {
        'Time': 'timestamp',
        'cnt': 'count',
        'temp': 'temperature',
    }
    transforms = {
        'timestamp': fact_mjd_to_datetime,
    }
    ignored_columns = ['QoS', ]


class BiasCurrentUncalibrated(AuxService):
    basename = "BIAS_CONTROL_CURRENT"
    renames = {
        'Time': 'timestamp',
        'I': 'bias_current',
    }
    transforms = {
        'timestamp': fact_mjd_to_datetime,
    }
    ignored_columns = ['QoS', ]


class BiasCurrentCalibrated(AuxService):
    basename = 'FEEDBACK_CALIBRATED_CURRENTS'
    renames = {
        'Time': 'timestamp',
        'I': 'bias_current',
    }
    transforms = {
        'timestamp': fact_mjd_to_datetime,
    }
    ignored_columns = [
        'QoS',
        'I_avg',
        'I_rms',
        'I_med',
        'I_dev',
        'N',
        'T_diff',
        'U_ov',
        'U_nom',
        'dU_temp',
    ]


class TriggerThresholds(AuxService):
    basename = 'FTM_CONTROL_STATIC_DATA'
    renames = {
        'Time': 'timestamp',
        'PatchThresh': 'patch_threshold',
    }
    transforms = {
        'timestamp': fact_mjd_to_datetime,
    }
    ignored_columns = [
        'QoS',
        'FTMtimeStamp',
        'GeneralSettings',
        'LEDStatus',
        'ActiveFTU',
        'TriggerInterval',
        'TriggerSeq',
        'LPSettings',
        'PhysTrigMult',
        'CalibTrigMult',
        'PhysTrigWindow',
        'CalibTrigWindow',
        'TrigDelay',
        'TMDelay',
        'DeadTime',
        'ClkCond',
        'PixEnabled',
        'PatchThresh',
        'Multiplicity',
        'Prescaling',
    ]
