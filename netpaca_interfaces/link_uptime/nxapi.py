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
This file contains the interface link-flap collector for Cisco NX-OS based
systems.  Based on current observations, there are three distinct types
of "uptime" duration formats:

    "07:20:17" - indicates 7 hours 20 minutes 17 seconds ago
    "6week(s) 1day(s)" - indicates 6 weeks and 1 day ago
    "3d04h" - indicates 3 day and 4 hours ago

Each of these different types need to be converted into "minutes ago"
for metric value consistency.
"""

# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import Optional, List
import re

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

import maya

from netpaca import Metric, MetricTimestamp
from netpaca.collectors.executor import CollectorExecutor
from netpaca.drivers.nxapi import Device

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netpaca_interfaces import link_uptime

# -----------------------------------------------------------------------------
# Exports (none)
# -----------------------------------------------------------------------------

__all__ = ["get_link_uptimes"]

# -----------------------------------------------------------------------------
#
#                                   CODE BEGINS
#
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
#
#                 Register Cisco Device NXAPI to Colletor Type
#
# -----------------------------------------------------------------------------


@link_uptime.register
async def start(
    device: Device, executor: CollectorExecutor, spec: link_uptime.CollectorModel
):
    """
    The IF DOM collector start coroutine for Cisco NX-API enabled devices.  The
    purpose of this coroutine is to start the collector task.  Nothing fancy.

    Parameters
    ----------
    device:
        The device driver instance for the Cisco device

    executor:
        The executor that is used to start one or more collector tasks. In this
        instance, there is only one collector task started per device.

    spec:
        The collector model instance that contains information about the
        collector; for example the collector configuration values.
    """
    device.log.info(f"{device.name}: Starting Cisco NXAPI Link Flap collection")

    executor.start(
        # required args
        spec=spec,
        coro=get_link_uptimes,
        device=device,
        # kwargs to collector coroutine:
        config=spec.config,
    )


# -----------------------------------------------------------------------------
#
#                             Collector Coroutine
#
# -----------------------------------------------------------------------------

_re_timestamp = re.compile(r"(?P<H>\d\d):(?P<M>\d\d):(?P<S>\d\d)")


async def get_link_uptimes(
    device: Device,
    timestamp: MetricTimestamp,                     # noqa unused
    config: link_uptime.LinkUptimeCollectorConfig,  # noqa unused
) -> Optional[List[Metric]]:
    """
    This coroutine will be executed as a asyncio Task on a periodic basis, the
    purpose is to collect data from the device and return the list Metrics.

    Parameters
    ----------
    device:
        The Cisco device driver instance for this device.

    timestamp: MetricTimestamp
        The current timestamp

    config:
        The collector configuration options

    Returns
    -------
    list of Metic items, or None
    """

    # wait for the interfaces collector to indicate that the data is available
    # for processing.

    interfaces = device.private["interfaces"]
    await interfaces["event"].wait()
    interfaces_xml = interfaces["data"]

    # find all of the interface records that have an eth_link_flapped element,
    # not all of them do.  We also want to exclude any record that has "never
    # flapped".  For each of these records we want to convert the value into an
    # "uptime in minutes" metric.

    iface_elist = interfaces_xml.xpath(
        'TABLE_interface/ROW_interface[eth_link_flapped[. != "never"]]'
    )

    dt_now = interfaces["maya_ts"]
    ts_now = interfaces["ts"]

    metrics = list()

    for rec in iface_elist:

        tags = dict(if_name=rec.findtext("interface"), if_desc=rec.findtext("desc"))

        last_flapped = rec.findtext("eth_link_flapped")

        # if the last_flapped value is in the "%H:%M:%S" format, then we need to
        # transform it into a duration format that can be consumed by the maya
        # package.

        if (mo := _re_timestamp.match(last_flapped)) is not None:
            last_flapped = "{}h{}m{}s".format(*mo.groups())

        if_uptime = dt_now - maya.when(last_flapped)
        if_uptime_min = if_uptime.total_seconds() // 60

        # TODO: skip any uptime that is greater than the configured threshold.

        metrics.append(
            link_uptime.LinkUptimeMetric(value=if_uptime_min, ts=ts_now, tags=tags)
        )

    return metrics
