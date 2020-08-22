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
References
----------
Working with Cisco ifLastChange values:
    https://github.com/netdisco/netdisco/issues/742
"""

# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import Optional, List

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netpaca import Metric, MetricTimestamp
from netpaca.collectors.executor import CollectorExecutor
from netpaca.drivers.ios_ssh import Device

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netpaca_interfaces import link_uptime

# -----------------------------------------------------------------------------
#
#                                   CODE BEGINS
#
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
#
#                       Collector Start Coroutine
#
# -----------------------------------------------------------------------------


@link_uptime.register
async def start(
    device: Device, executor: CollectorExecutor, spec: link_uptime.CollectorModel
):
    """
    Interface link-uptime metric collector for Cisco IOS SSH/SNMP devices.

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
#                             Metric Collector Coroutine
#
# -----------------------------------------------------------------------------


async def get_link_uptimes(
    device: Device,
    timestamp: MetricTimestamp,  # noqa not used
    config: link_uptime.LinkUptimeCollectorConfig,  # noqa
) -> Optional[List[Metric]]:

    # wait for the interfaces collector to indicate that the data is available
    # for processing.

    interfaces = device.private["interfaces"]
    await interfaces["event"].wait()

    # now process the collected interface data for link uptime ....

    dev_uptime_wrapped = device.private["sys_uptime_wrapped"]
    did_wrap = dev_uptime_wrapped > 0
    ifs_data = interfaces["data"]
    ifs_data_ts = interfaces["ts"]
    sys_uptime = device.private["sys_uptime"]

    metrics = list()

    for if_name, if_rec in ifs_data.items():

        # skip any interfaces that are not link-up
        if if_rec["if_link_up"] is False:
            continue

        # skip any interface that have ifLastChange == 0 (never)
        if (if_lc := if_rec["if_lastchange"]) == 0:
            continue

        # need to change scenarios where sysUpTime may have wrapped.  code
        # lifted from Netdisco project per cited References.

        if did_wrap and if_lc < sys_uptime:
            # ambiguous: lastchange could be sysUptime before or after wrap

            if sys_uptime > 30_000 and if_lc < 30_000:
                # uptime wrap more than 5min ago but lastchange within 5min
                # assume lastchange was directly after boot -> no action
                pass

            else:
                # uptime wrap less than 5min ago or lastchange > 5min ago
                # to be on safe side, assume lastchange after counter wrap
                device.log.warning(
                    f"{device.name}:{if_name} - correcting ifLastChange, "
                    "assuming sysUpTime wrap"
                )
                if_lc += dev_uptime_wrapped * 2 ** 32

        # add the interface link-uptime metric.

        if_uptime_m = (sys_uptime - if_lc) // 6_000

        metrics.append(
            link_uptime.LinkUptimeMetric(
                ts=ifs_data_ts,
                tags=dict(if_name=if_name, if_desc=if_rec["if_desc"]),
                value=if_uptime_m,
            )
        )

    # done looping through interfaces, return metric list
    return metrics
