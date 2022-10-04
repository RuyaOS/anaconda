#
# Kickstart handler for packaging.
#
# Copyright (C) 2018 Red Hat, Inc.
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
from pyanaconda.core.constants import URL_TYPE_BASEURL, URL_TYPE_MIRRORLIST, URL_TYPE_METALINK, \
    DNF_DEFAULT_REPO_COST
from pyanaconda.modules.common.structures.payload import RepoConfigurationData
from pykickstart.errors import KickstartParseError
from pykickstart.parser import Packages, Group
from pykickstart.sections import PackageSection
from pykickstart.constants import KS_BROKEN_IGNORE, GROUP_DEFAULT

from pyanaconda.core.configuration.anaconda import conf
from pyanaconda.core.i18n import _
from pyanaconda.core.kickstart import KickstartSpecification, commands as COMMANDS


def convert_ks_repo_to_repo_data(ks_data):
    """Convert the kickstart command into a repo configuration.

    :param RepoData ks_data: a kickstart data
    :return RepoConfigurationData: a repo configuration
    """
    if not isinstance(ks_data, COMMANDS.RepoData):
        raise ValueError("Unexpected kickstart data: {}".format(type(ks_data)))

    repo_data = RepoConfigurationData()
    repo_data.name = ks_data.name

    if ks_data.baseurl:
        repo_data.url = ks_data.baseurl
        repo_data.type = URL_TYPE_BASEURL
    elif ks_data.mirrorlist:
        repo_data.url = ks_data.mirrorlist
        repo_data.type = URL_TYPE_MIRRORLIST
    elif ks_data.metalink:
        repo_data.url = ks_data.metalink
        repo_data.type = URL_TYPE_METALINK
    else:
        # Handle the `repo --name=updates` use case.
        # FIXME: Find a better solution for this use case.
        repo_data.url = ""
        repo_data.type = "NONE"

    repo_data.proxy = ks_data.proxy or ""
    repo_data.cost = ks_data.cost or DNF_DEFAULT_REPO_COST
    repo_data.included_packages = ks_data.includepkgs
    repo_data.excluded_packages = ks_data.excludepkgs

    repo_data.ssl_verification_enabled = not ks_data.noverifyssl
    repo_data.ssl_configuration.ca_cert_path = ks_data.sslcacert or ""
    repo_data.ssl_configuration.client_cert_path = ks_data.sslclientcert or ""
    repo_data.ssl_configuration.client_key_path = ks_data.sslclientkey or ""

    return repo_data


def convert_repo_data_to_ks_repo(repo_data):
    """Convert the repo configuration into a kickstart command.

    :param RepoConfigurationData repo_data: a repo configuration
    :return RepoData: a kickstart data
    """
    if not isinstance(repo_data, RepoConfigurationData):
        raise ValueError("Unexpected data: {}".format(type(repo_data)))

    ks_data = COMMANDS.RepoData()
    ks_data.name = repo_data.name

    if repo_data.type == URL_TYPE_BASEURL:
        ks_data.baseurl = repo_data.url
    elif repo_data.type == URL_TYPE_MIRRORLIST:
        ks_data.mirrorlist = repo_data.url
    elif repo_data.type == URL_TYPE_METALINK:
        ks_data.metalink = repo_data.url

    ks_data.proxy = repo_data.proxy
    ks_data.noverifyssl = not repo_data.ssl_verification_enabled
    ks_data.sslcacert = repo_data.ssl_configuration.ca_cert_path
    ks_data.sslclientcert = repo_data.ssl_configuration.client_cert_path
    ks_data.sslclientkey = repo_data.ssl_configuration.client_key_path

    if repo_data.cost != DNF_DEFAULT_REPO_COST:
        ks_data.cost = repo_data.cost

    ks_data.includepkgs = repo_data.included_packages
    ks_data.excludepkgs = repo_data.excluded_packages

    return ks_data


class AnacondaPackageSection(PackageSection):
    """The parser of the %packages kickstart section."""

    def handleHeader(self, lineno, args):
        """Process packages section header.

        Add checks based on configuration settings.
        """
        super().handleHeader(lineno, args)

        if not conf.payload.enable_ignore_broken_packages \
           and self.handler.packages.handleBroken == KS_BROKEN_IGNORE:
            raise KickstartParseError(
                _("The %packages --ignorebroken feature is not supported on your product!"),
                lineno=lineno
            )


class AnacondaPackages(Packages):
    """The representation of the %packages kickstart section."""

    def create_group(self, name, include=GROUP_DEFAULT):
        """Create a new instance of a group.

        :param name: a name of the group
        :param include: a level of inclusion
        :return: a group object
        """
        return Group(name=name, include=include)


class PayloadKickstartSpecification(KickstartSpecification):

    commands = {
        "cdrom": COMMANDS.Cdrom,
        "harddrive": COMMANDS.HardDrive,
        "hmc": COMMANDS.Hmc,
        "liveimg": COMMANDS.Liveimg,
        "module": COMMANDS.Module,
        "nfs": COMMANDS.NFS,
        "ostreesetup": COMMANDS.OSTreeSetup,
        "url": COMMANDS.Url
    }

    commands_data = {
        "ModuleData": COMMANDS.ModuleData
    }

    sections = {
        "packages": AnacondaPackageSection
    }

    sections_data = {
        "packages": AnacondaPackages
    }
