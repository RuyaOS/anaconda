#
# DBus interface for the storage checker module
#
# Copyright (C) 2019 Red Hat, Inc.
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
from dasbus.server.interface import dbus_interface
from dasbus.typing import *  # pylint: disable=wildcard-import
from pyanaconda.modules.common.base.base_template import InterfaceTemplate
from pyanaconda.modules.common.constants.objects import STORAGE_CHECKER

__all__ = ["StorageCheckerInterface"]


@dbus_interface(STORAGE_CHECKER.interface_name)
class StorageCheckerInterface(InterfaceTemplate):
    """DBus interface for the storage checker module."""

    def SetConstraint(self, name: Str, value: Variant):
        """Set a constraint to a new value.

        Supported constraints:
            min_ram  Minimal size of the total memory in bytes.
            swap_is_recommended  Recommend to specify a swap partition.

        :param str name: a name of the existing constraint
        :param value: a value of the constraint
        :raise: UnsupportedValueError if the constraint is not supported
        """
        self.implementation.set_constraint(name, get_native(value))
