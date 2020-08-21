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
This file contains the collctor definition for Link Flap.
"""

from typing import Optional
from pydantic.dataclasses import dataclass
from pydantic import Field, BaseModel

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


class LinkFlapCollectorConfig(CollectorConfigModel):
    uptime_threshold: Optional[int] = Field(
        default=False,
        description="""\
Use this value to exclude interfaces that have been up for longer than
$uptime_threshold minutes.  For example 1 day is 3_840 minutes.
""",
    )


class LinkFlapCollectorTags(BaseModel):
    if_name: str = Field(description='interface name')
    if_desc: str = Field(description='interface description')


# -----------------------------------------------------------------------------
#
#                              Metrics
#
# -----------------------------------------------------------------------------
# This section defines the Metric types supported by the Link Flap Collector
# -----------------------------------------------------------------------------

@dataclass
class LinkUptimeMetric(Metric):
    """ Link uptime in minutes """
    value: int
    name: str = "linkflap_uptime"


# -----------------------------------------------------------------------------
#
#                              Collector Definition
#
# -----------------------------------------------------------------------------


class LinkFlapCollectorType(CollectorType):
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

    name = "linkflap"
    description = """
Used to collect interface uptime (last flap) metrics
"""
    config = LinkFlapCollectorConfig
    tags: LinkFlapCollectorTags
    metrics = [LinkUptimeMetric]


# create an "alias" variable so that the device specific collector packages
# can register their start functions.

name = LinkFlapCollectorType.name
register = LinkFlapCollectorType.start.register
