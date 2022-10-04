#
# Copyright (C) 2013, 2017  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#

"""
A GeoIP and WiFi location module - location detection based on IP address

=================================
How to use the geolocation module
=================================

   First call init_geolocation() with appropriate parameters - this creates
   the Geolocation singleton and specifies what geolocation provider will be
   used.

   To actually look up current position, call the refresh() function of the
   singleton, this will trigger the actual online geolocation query, which
   runs in a thread.

   It's possible to wait for the lookup to finish by calling the
   wait_for_refresh_to_finish() method of the singleton. If a lookup is in
   progress it will block until the lookup finishes or a timeout is reached.
   If no lookup is in progress it will return at once.

   After the look-up thread finishes, the results are stored in the singleton
   and can be retrieved using the territory, timezone and result properties.

   If you use these properties without calling refresh() first or if the
   look-up is currently in progress or failed to return any results, all
   properties will return None.

====================
Geolocation backends
====================

Two geolocation backends are currently supported:
   * Fedora GeoIP API
   * Hostip GeoIP

Fedora GeoIP backend

   This is the default backend. It queries the Fedora GeoIP API for location
   data based on current public IP address. The reply is JSON formatted and
   contains the following fields:
   postal_code, latitude, longitude, region, city, country_code, country_name,
   time_zone, country_code3, area_code, metro_code, region_name and dma_code
   Anaconda currently uses just time_zone and country_code.

Hostip backend

   A GeoIP look-up backend that can be used to determine current country code
   from current public IP address. The public IP address is determined
   automatically when calling the API.
   GeoIP results from Hostip contain the current public IP and an approximate
   address. To get this detail location info, use the result property to get
   an instance of the LocationResult class, used to wrap the lookup result.

==========================
Possible issues with GeoIP
==========================

   "I'm in Switzerland connected to corporate VPN and anaconda tells me
   I'm in the Netherlands."

   The public IP address is not directly mapped to the physical location
   of a computer. So while your world visible IP address is registered to
   an IP block assigned to an ISP in Netherlands, it is just the external
   address of the Internet gateway of  your corporate network.
   As VPNs and proxies can connect two computers anywhere on Earth,
   this issue is unfortunately probably unsolvable.


Backends that could possibly be used in the future

GPS geolocation

    + doesn't leak your coordinates to a third party
      (not entirely true for assisted GPS)
    - unassisted cold GPS startup can take tens of minutes to acquire a GPS fix
    + assisted GPS startup (as used in most smartphones) can acquire a fix
      in a couple seconds

cell tower geolocation

   + cell tower id could be queried against a cell tower database to find approximate region
   + fully passive (with local cell tower database)
   - needs a phone modem
   - must store up to date cell tower database

"""
from pyanaconda.core.util import requests_session
import requests
import threading
import time
from pyanaconda import network

from pyanaconda.anaconda_loggers import get_module_logger, get_sensitive_info_logger
log = get_module_logger(__name__)
sensitive_info_log = get_sensitive_info_logger()

from pyanaconda.core import constants
from pyanaconda.core.configuration.anaconda import conf
from pyanaconda.threading import AnacondaThread, threadMgr
from pyanaconda.timezone import get_preferred_timezone, is_valid_timezone
from pyanaconda.flags import flags

OFFICIALLY_SUPPORTED_GEOLOCATION_PROVIDER_IDS = {
    constants.GEOLOC_PROVIDER_FEDORA_GEOIP,
    constants.GEOLOC_PROVIDER_HOSTIP
}


class Geolocation(object):
    """Top level geolocation handler."""

    def __init__(self, geoloc_option=None, options_override=False):
        """Prepare the geolocation module for handling geolocation queries.

        This sets-up the Geolocation instance with the given geolocation_provider (or using the
        default one if no provider is given. Please note that calling this method doesn't actually
        execute any queries by itself, you need to call refresh() to do that.

        :param geoloc_option: what was passed in boot or command line options
        :type geoloc_option: str or None
        :param options_override:
        :type options_override: bool
        """
        self._geolocation_enabled = self._check_if_geolocation_should_be_used(geoloc_option,
                                                                              options_override)
        provider_id = constants.GEOLOC_DEFAULT_PROVIDER

        # check if a provider was specified by an option
        if geoloc_option is not None and self._geolocation_enabled:
            parsed_id = self._get_provider_id_from_option(geoloc_option)
            if parsed_id is None:
                log.error('geoloc: wrong provider id specified: %s', geoloc_option)
            else:
                provider_id = parsed_id

        self._location_info = LocationInfo(provider_id=provider_id)

    def _check_if_geolocation_should_be_used(self, geoloc_option, options_override):
        """Check if geolocation can be used during this installation run.

        And set the geolocation_enabled module attribute accordingly.

        The result is based on current installation type - fully interactive vs
        fully or partially automated kickstart installation and on the state of the
        "geoloc*" boot/CLI options.

        By default geolocation is not enabled during a kickstart based installation,
        unless the geoloc_use_with_ks boot/CLI option is used.

        Also the geoloc boot/CLI option can be used to make sure geolocation
        will not be used during an installation, like this:

        inst.geoloc=0

        :param geoloc_option: what was passed in boot or command line options
        :type geoloc_option: str or None
        :param options_override: use with kickstart due to CLI/boot option override
        :type options_override: bool
        """
        # don't use geolocation during image and directory installation
        if not conf.target.is_hardware:
            log.info("Geolocation is disabled for image or directory installation.")
            return False

        # check if geolocation was not disabled by boot or command line option
        # our documentation mentions only "0" as the way to disable it
        if str(geoloc_option).strip() == "0":
            log.info("Geolocation is disabled by the geoloc option.")
            return False

        # don't use geolocation during kickstart installation unless explicitly
        # requested by the user
        if flags.automatedInstall:
            if options_override:
                # check for use-with-kickstart overrides
                log.info("Geolocation is enabled during kickstart installation due to use of "
                         "the geoloc-use-with-ks option.")
                return True
            else:
                # otherwise disable geolocation during a kickstart installation
                log.info("Geolocation is disabled due to automated kickstart based installation.")
                return False

        log.info("Geolocation is enabled.")
        return True

    def refresh(self):
        """Refresh information about current location."""
        self._location_info.refresh()

    def wait_for_refresh_to_finish(self, timeout=constants.GEOLOC_TIMEOUT):
        """Wait for the Geolocation lookup to finish.

        If there is no lookup in progress (no Geolocation refresh thread
        is running), this function returns at once.

        :param float timeout: how many seconds to wait before timing out
        """
        start_time = time.time()
        self._location_info.refresh_condition.acquire()
        if self._location_info.refresh_in_progress:
            # calling wait releases the lock and blocks,
            # after the thread is notified, it unblocks and
            # reacquires the lock
            self._location_info.refresh_condition.wait(timeout=timeout)
            if self._location_info.refresh_in_progress:
                log.info("Waiting for Geolocation timed out after %d seconds.", timeout)
                # please note that this does not mean that the actual
                # geolocation lookup was stopped in any way, it just
                # means the caller was unblocked after the waiting period
                # ended while the lookup thread is still running
            else:
                elapsed_time = time.time() - start_time
                log.info("Waited %1.2f seconds for Geolocation", elapsed_time)
        self._location_info.refresh_condition.release()

    @property
    def enabled(self):
        """Report if geolocation is enabled."""
        return self._geolocation_enabled

    @property
    def result(self):
        """Returns the current geolocation result wrapper.

        None might be returned if:

        - no results were found
        - the refresh is still in progress

        :return: :class:LocationResult instance or None if location is unknown
        :rtype: :class:LocationResult instance or None
        """
        return self._location_info.result

    def _get_provider_id_from_option(self, option_string):
        """Get a valid provider id from a string.

        This function is used to parse command line
        arguments/boot options for the geolocation module.

        :param str option_string: option specifying the provider
        :return: provider id
        """
        # normalize the option string, just in case
        option_string = option_string.lower()
        if option_string.lower() in OFFICIALLY_SUPPORTED_GEOLOCATION_PROVIDER_IDS:
            return option_string
        else:
            # fall back to the default provider
            return None


class LocationInfo(object):
    """Determines current location.

    Determines current location based on IP address.
    """

    def __init__(self, provider_id=constants.GEOLOC_DEFAULT_PROVIDER):
        """
        :param str provider_id: GeoIP provider id
        """
        available_providers = {
            constants.GEOLOC_PROVIDER_FEDORA_GEOIP: FedoraGeoIPProvider,
            constants.GEOLOC_PROVIDER_HOSTIP: HostipGeoIPProvider,
        }
        provider = available_providers.get(provider_id, FedoraGeoIPProvider)
        self._provider = provider()

    @property
    def result(self):
        """Return the lookup result."""
        return self._provider.result

    def refresh(self):
        """Refresh location info."""
        # check if a refresh is already in progress
        if threadMgr.get(constants.THREAD_GEOLOCATION_REFRESH):
            log.debug("Geoloc: refresh already in progress")
        else:  # wait for Internet connectivity
            if network.wait_for_connectivity():
                threadMgr.add(AnacondaThread(
                    name=constants.THREAD_GEOLOCATION_REFRESH,
                    target=self._provider.refresh))
            else:
                log.error("Geolocation refresh failed"
                          " - no connectivity")

    @property
    def refresh_in_progress(self):
        """Report if refresh is in progress."""
        return self._provider.refresh_in_progress

    @property
    def refresh_condition(self):
        """Provide access to the Refresh condition of the provider.

        So that users of this class can wait for the location lookup to finish.
        """
        return self._provider.refresh_condition


class LocationResult(object):
    """Encapsulates the result from GeoIP lookup."""

    def __init__(self, territory_code=None, timezone=None,
                 timezone_source="unknown", public_ip_address=None, city=None):
        """
        :param territory_code: the territory code from GeoIP lookup
        :type territory_code: string
        :param timezone: the time zone from GeoIP lookup
        :type timezone: string
        :param timezone_source: specifies source of the time zone string
        :type timezone_source: string
        :param public_ip_address: current public IP address
        :type public_ip_address: string
        :param city: current city
        :type city: string
        """
        self._territory_code = territory_code
        self._timezone = timezone
        self._timezone_source = timezone_source
        self._public_ip_address = public_ip_address
        self._city = city

    @property
    def territory_code(self):
        return self._territory_code

    @property
    def timezone(self):
        return self._timezone

    @property
    def public_ip_address(self):
        return self._public_ip_address

    @property
    def city(self):
        return self._city

    def __str__(self):
        if self.territory_code:
            result_string = "territory: %s" % self.territory_code
            if self.timezone:
                result_string += "\ntime zone: %s (from %s)" % (
                    self.timezone, self._timezone_source
                )
            if self.public_ip_address:
                result_string += "\npublic IP address: "
                result_string += "%s" % self.public_ip_address
            if self.city:
                result_string += "\ncity: %s" % self.city
            return result_string
        else:
            return "Position unknown"


class GeolocationBackend(object):
    """Base class for GeoIP backends."""
    def __init__(self):
        self._result = LocationResult()
        self._result_lock = threading.Lock()
        self._session = requests_session()
        self._refresh_condition = threading.Condition()
        self._refresh_in_progress = False

    @property
    def name(self):
        """Get name of the backend

        :return: name of the backend
        :rtype: string
        """
        pass

    def refresh(self):
        """Refresh the geolocation data."""
        # check if refresh is needed
        log.info("Starting geolocation lookup")
        log.info("Geolocation provider: %s", self.name)
        with self._refresh_condition:
            self._refresh_in_progress = True

        start_time = time.time()
        self._refresh()
        log.info("Geolocation lookup finished in %1.1f seconds",
                 time.time() - start_time)

        with self._refresh_condition:
            self._refresh_in_progress = False
            self._refresh_condition.notify_all()
        # check if there were any results
        if self.result:
            log.info("got results from geolocation")
            sensitive_info_log.info("geolocation result:\n%s", self.result)
        else:
            log.info("no results from geolocation")

    def _refresh(self):
        pass

    @property
    def refresh_in_progress(self):
        """Report if location refresh is in progress."""
        with self._refresh_condition:
            return self._refresh_in_progress

    @property
    def refresh_condition(self):
        """Return a Condition instance that can be used to wait for the refresh to finish."""
        return self._refresh_condition

    @property
    def result(self):
        """Current location.

        :return: geolocation lookup result
        :rtype: LocationResult
        """
        with self._result_lock:
            return self._result

    def _set_result(self, new_result):
        with self._result_lock:
            self._result = new_result

    def __str__(self):
        return self.name


class FedoraGeoIPProvider(GeolocationBackend):
    """The Fedora GeoIP service provider."""

    API_URL = "https://geoip.fedoraproject.org/city"

    @property
    def name(self):
        return "Fedora GeoIP"

    def _refresh(self):
        try:
            reply = self._session.get(self.API_URL,
                                      timeout=constants.GEOLOC_CONNECTION_TIMEOUT,
                                      verify=True)
            if reply.status_code == requests.codes.ok:
                json_reply = reply.json()
                territory = json_reply.get("country_code", None)
                timezone_source = "GeoIP"
                timezone_code = json_reply.get("time_zone", None)

                # check if the timezone returned by the API is valid
                if not is_valid_timezone(timezone_code):
                    # try to get a timezone from the territory code
                    timezone_code = get_preferred_timezone(territory)
                    timezone_source = "territory code"
                if territory or timezone_code:
                    self._set_result(LocationResult(territory_code=territory,
                                                    timezone=timezone_code,
                                                    timezone_source=timezone_source))
            else:
                log.error("Geoloc: Fedora GeoIP API lookup failed with status code: %s",
                          reply.status_code)
        except requests.exceptions.RequestException as e:
            log.debug("Geoloc: RequestException for Fedora GeoIP API lookup:\n%s", e)
        except ValueError as e:
            log.debug("Geoloc: Unable to decode GeoIP JSON:\n%s", e)


class HostipGeoIPProvider(GeolocationBackend):
    """The Hostip GeoIP service provider."""

    API_URL = "http://api.hostip.info/get_json.php"

    @property
    def name(self):
        return "Hostip.info"

    def _refresh(self):
        try:
            reply = self._session.get(self.API_URL,
                                      timeout=constants.GEOLOC_CONNECTION_TIMEOUT,
                                      verify=True)
            if reply.status_code == requests.codes.ok:
                reply_dict = reply.json()
                territory = reply_dict.get("country_code", None)

                # unless at least country_code is available,
                # we don't return any results
                if territory is not None:
                    self._set_result(LocationResult(territory_code=territory,
                                                    public_ip_address=reply_dict.get("ip", None),
                                                    city=reply_dict.get("city", None)))
            else:
                log.error("Geoloc: Hostip lookup failed with status code: %s", reply.status_code)
        except requests.exceptions.RequestException as e:
            log.debug("Geoloc: RequestException during Hostip lookup:\n%s", e)
        except ValueError as e:
            log.debug("Geoloc: Unable to decode Hostip JSON:\n%s", e)

geoloc = None


def init_geolocation(geoloc_option, options_override):
    """Initialize the geolocation singleton."""
    global geoloc
    geoloc = Geolocation(geoloc_option=geoloc_option, options_override=options_override)
