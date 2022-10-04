#
# Copyright (C) 2021  Red Hat, Inc.
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
from pyanaconda.anaconda_loggers import get_module_logger
from pyanaconda.core.i18n import _
from pyanaconda.modules.common.structures.packages import PackagesSelectionData

log = get_module_logger(__name__)


def is_software_selection_complete(dnf_manager, selection, kickstarted=False):
    """Check the completeness of the software selection.

    :param dnf_manager: a DNF manager
    :param selection: a packages selection data
    :param kickstarted: is the selection configured by a kickstart file?
    :return: True if the selection is complete, otherwise False
    """
    # The environment doesn't have to be set for the automated installation.
    if kickstarted and not selection.environment:
        return True

    # The selected environment has to be valid.
    return dnf_manager.is_environment_valid(selection.environment)


def get_software_selection_status(dnf_manager, selection, kickstarted=False):
    """Get the software selection status.

    :param dnf_manager: a DNF manager
    :param selection: a packages selection data
    :param kickstarted: is the selection configured by a kickstart file?
    :return: a translated string with the selection status
    """
    if kickstarted:
        # The %packages section is present in kickstart, but environment is not set.
        if not selection.environment:
            return _("Custom software selected")
        # The environment is set to an invalid value.
        elif not dnf_manager.is_environment_valid(selection.environment):
            return _("Invalid environment specified in kickstart")
    else:
        if not selection.environment:
            # No environment is set.
            return _("Please confirm software selection")
        elif not dnf_manager.is_environment_valid(selection.environment):
            # Selected environment is not valid, this can happen when a valid environment
            # is selected (by default, manually or from kickstart) and then the installation
            # source is switched to one where the selected environment is no longer valid.
            return _("Selected environment is not valid")

    # The valid environment is set.
    environment_data = dnf_manager.get_environment_data(selection.environment)
    return environment_data.name


class SoftwareSelectionCache(object):
    """The cache of the user software selection.

    Use the software selection cache to select environments
    and groups in the user interface.

    The cache remembers groups that were selected by default
    based on the current environment, explicitly selected by
    the user and explicitly deselected.

    Selected groups that are not available in the current
    environment are ignored.
    """

    def __init__(self, dnf_manager):
        """Create a new cache.

        :param dnf_manager: a DNF manager
        """
        self._dnf_manager = dnf_manager
        self._environment = ""
        self._available_groups = set()
        self._default_groups = set()
        self._selected_groups = set()
        self._deselected_groups = set()

    @property
    def environment(self):
        """The selected environment.

        :return: an environment id
        """
        return self._environment

    @property
    def available_environments(self):
        """The available environments.

        :return: a list of environment ids
        """
        return self._dnf_manager.environments

    @property
    def groups(self):
        """The selected groups.

        :return: a list of group ids
        """
        return sorted(filter(self.is_group_selected, self._available_groups))

    @property
    def available_groups(self):
        """The available groups.

        :return: a list of group ids
        """
        return sorted(self._available_groups)

    def select_environment(self, environment):
        """Select the specified environment.

        :param str environment: an identifier of an environment
        """
        log.debug("Selecting the '%s' environment.", environment)

        # Reset the environment configuration.
        self._environment = ""
        self._default_groups = set()
        self._available_groups = set()

        # No environment is specified.
        if not environment:
            return

        # Get the environment data.
        environment_data = self._dnf_manager.get_environment_data(environment)

        # Select the environment.
        self._environment = environment_data.id

        # Select the default groups.
        self._default_groups = set(environment_data.default_groups)

        # Select the available groups.
        self._available_groups = set(environment_data.get_available_groups())

    def is_environment_selected(self, environment):
        """Is the specified environment marked as selected?

        :param str environment: an identifier of an environment
        :return: True if the environment is marked as selected, otherwise False
        """
        return environment == self._environment

    def select_group(self, group):
        """Select the specified group.

        :param str group: an identifier of a group
        """
        log.debug("Selecting the '%s' group.", group)

        # Get the group data.
        group_data = self._dnf_manager.get_group_data(group)

        # Remove the group from the deselected groups.
        self._deselected_groups.discard(group_data.id)

        # Add the group to the selected groups if it is not a default.
        if group_data.id not in self._default_groups:
            self._selected_groups.add(group_data.id)

    def deselect_group(self, group):
        """Select or deselect the specified group.

        :param str group: an identifier of a group
        """
        log.debug("Deselecting the '%s' group.", group)

        # Get the group data.
        group_data = self._dnf_manager.get_group_data(group)

        # Add the group to the deselected groups. We don't need
        # to remove the group from selected or default groups,
        # because deselected groups have a higher priority.
        self._deselected_groups.add(group_data.id)

    def is_group_selected(self, group):
        """Is the specified group marked as selected?

        :param str group: an identifier of a group
        :return: True if the group is marked as selected, otherwise False
        """
        # The group is not available in the current environment.
        if group not in self._available_groups:
            return False

        # The group is explicitly deselected by the user.
        if group in self._deselected_groups:
            return False

        # The group is selected by default or by the user.
        return group in self._default_groups or group in self._selected_groups

    def apply_selection_data(self, selection: PackagesSelectionData):
        """Apply the selection data.

        Invalid environments and groups will be ignored. If the environment
        cannot be selected, we will choose a default one.

        :param selection: a packages selection data
        """
        # Select the environment.
        if self._dnf_manager.resolve_environment(selection.environment):
            self.select_environment(selection.environment)
        else:
            log.warning("The '%s' environment couldn't be selected.", selection.environment)
            self.select_environment(self._dnf_manager.default_environment)

        # Select groups.
        self._selected_groups = set()
        self._deselected_groups = set()

        for group in selection.groups:
            if self._dnf_manager.resolve_group(group):
                self.select_group(group)
                continue

            log.warning("The '%s' group couldn't be selected.", group)

    def get_selection_data(self) -> PackagesSelectionData:
        """Generate the selection data.

        :return: a packages selection data
        """
        selection = PackagesSelectionData()
        selection.environment = self.environment
        selection.groups = self.groups
        return selection
