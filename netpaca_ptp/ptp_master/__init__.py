#  Copyright (C) 2020  Jeremy Schulman
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
This file contains the collctor definition for monitoring link flaps.
"""

from pydantic.dataclasses import dataclass

from netpaca import Metric
from netpaca.collectors import CollectorType, CollectorConfigModel
from netpaca.config_model import CollectorModel  # noqa

# -----------------------------------------------------------------------------
#
#                              Collector Config
# -----------------------------------------------------------------------------
# Define the collector configuraiton options that the User can set in their
# configuration file.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
#
#                              Metrics
#
# -----------------------------------------------------------------------------
# This section defines the Metric types supported by the Link Flap Collector
# -----------------------------------------------------------------------------


@dataclass
class PtpMasterClassMetric(Metric):
    """ Link uptime in minutes """

    value: int
    name: str = "ptp_master_class"


# -----------------------------------------------------------------------------
#
#                              Collector Definition
#
# -----------------------------------------------------------------------------


class PtpMasterCollectorType(CollectorType):
    """
    This class defines the Link Flap collector specification.  This class is
    "registered" with the "netpaca.collectors" entry_point group via the
    `setup.py` file.  As a result of this registration, a User of the netpaca
    tool can setup their configuration file with the "use" statement.

    Examples (Configuration File)
    -----------------------------
    [collectors.linkflap]
        use = "netpaca.collectors:linkflap"
    """

    name = "ptp-master"

    description = """
Collects PTP master metrics
"""
    metrics = [PtpMasterClassMetric]


# create an "alias" variable so that the device specific collector packages
# can register their start functions.

name = PtpMasterCollectorType.name
register = PtpMasterCollectorType.start.register
