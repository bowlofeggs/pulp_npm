from gettext import gettext as _

from pulp.client.commands.repo import cudl, status, sync_publish
from pulp.client.extensions.decorator import priority

from pulp_npm.common import constants
from pulp_npm.extensions.admin import packages, upload
from pulp_npm.extensions.admin.cudl import (
    CreateNpmRepositoryCommand, ListNpmRepositoriesCommand, UpdateNpmRepositoryCommand)


SECTION_ROOT = 'npm'
DESC_ROOT = _('manage npm repositories')

SECTION_REPO = 'repo'
DESC_REPO = _('repository lifecycle commands')

SECTION_PUBLISH = 'publish'
DESC_PUBLISH = _('publish a npm repository')

SECTION_SYNC = 'sync'
DESC_SYNC = _('sync a npm repository from an upstream repository')


@priority()
def initialize(context):
    """
    Create the Npm CLI section and add it to the root

    :param context: the CLI context.
    :type  context: pulp.client.extensions.core.ClientContext
    """
    root_section = context.cli.create_section(SECTION_ROOT, DESC_ROOT)
    _add_repo_section(context, root_section)


def _add_repo_section(context, parent_section):
    """
    add a repo section to the Npm section

    :param context:         The client context
    :type  context:         pulp.client.extensions.core.ClientContext
    :param parent_section:  section of the CLI to which the repo section
                            should be added
    :type  parent_section:  pulp.client.extensions.extensions.PulpCliSection
    """
    repo_section = parent_section.create_subsection(SECTION_REPO, DESC_REPO)

    repo_section.add_command(CreateNpmRepositoryCommand(context))
    repo_section.add_command(UpdateNpmRepositoryCommand(context))
    repo_section.add_command(cudl.DeleteRepositoryCommand(context))
    repo_section.add_command(ListNpmRepositoriesCommand(context))

    _add_publish_section(context, repo_section)
    _add_sync_section(context, repo_section)

    repo_section.add_command(upload.UploadPackageCommand(context))
    repo_section.add_command(packages.RemovePackagesCommand(context))
    repo_section.add_command(packages.CopyPackagesCommand(context))
    repo_section.add_command(packages.ListPackagesCommand(context))


def _add_publish_section(context, parent_section):
    """
    add a publish section to the repo section

    :param context:        The client context
    :type  context:        pulp.client.extensions.core.ClientContext
    :param parent_section: section of the CLI to which the repo section should be added
    :type  parent_section: pulp.client.extensions.extensions.PulpCliSection
    """
    section = parent_section.create_subsection(SECTION_PUBLISH, DESC_PUBLISH)

    renderer = status.PublishStepStatusRenderer(context)
    section.add_command(
        sync_publish.RunPublishRepositoryCommand(context,
                                                 renderer,
                                                 constants.CLI_DISTRIBUTOR_ID))
    section.add_command(
        sync_publish.PublishStatusCommand(context, renderer))


def _add_sync_section(context, parent_section):
    """
    add a sync section

    :param context:        pulp context
    :type  context:        pulp.client.extensions.core.ClientContext
    :param parent_section: section of the CLI to which the upload section
                           should be added
    :type  parent_section: pulp.client.extensions.extensions.PulpCliSection
    :return:               populated section
    :rtype:                PulpCliSection
    """
    renderer = status.PublishStepStatusRenderer(context)

    sync_section = parent_section.create_subsection(SECTION_SYNC, DESC_SYNC)
    sync_section.add_command(sync_publish.RunSyncRepositoryCommand(context, renderer))
