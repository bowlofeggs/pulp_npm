from gettext import gettext as _

from okaara import parsers
from pulp.client import arg_utils
from pulp.client.commands.repo.cudl import CreateAndConfigureRepositoryCommand
from pulp.client.commands.repo.cudl import ListRepositoriesCommand
from pulp.client.commands.repo.cudl import UpdateRepositoryCommand
from pulp.client.commands.repo.importer_config import ImporterConfigMixin
from pulp.client.extensions.extensions import PulpCliOption
from pulp.common.constants import REPO_NOTE_TYPE_KEY

from pulp_npm.common import constants


d = _('if "true", on each successful sync the repository will automatically be '
      'published; if "false" content will only be available after manually publishing '
      'the repository; defaults to "true"')
OPT_AUTO_PUBLISH = PulpCliOption('--auto-publish', d, required=False,
                                 parse_func=parsers.parse_boolean)
d = _('a comma separated list of package names you wish Pulp to sync')
OPT_PACKAGE_NAMES = PulpCliOption('--package-names', d, required=False)

DESC_FEED = _('URL for the upstream npm repo')

IMPORTER_CONFIGURATION_FLAGS = dict(
    include_ssl=False,
    include_sync=True,
    include_unit_policy=False,
    include_proxy=False,
    include_throttling=False
)


class NpmRepositoryOptions(object):
    """
    A mixin to provide the same custom options to the create and update commands.
    """

    def __init__(self):
        """
        Initialize the NpmRepositoryOptions object.
        """
        self.add_option(OPT_AUTO_PUBLISH)
        self.add_option(OPT_PACKAGE_NAMES)
        self.options_bundle.opt_feed.description = DESC_FEED

    def _describe_distributors(self, user_input):
        """
        Subclasses should override this to provide whatever option parsing
        is needed to create distributor configs.

        :param user_input: dictionary of data passed in by okaara
        :type  user_input: dict
        :return:           list of dict containing distributor_type_id,
                           repo_plugin_config, auto_publish, and distributor_id (the same
                           that would be passed to the RepoDistributorAPI.create call).
        :rtype:            list of dict
        """
        config = {}
        auto_publish = user_input.get(OPT_AUTO_PUBLISH.keyword)

        if auto_publish is None:
            auto_publish = True

        data = [
            dict(distributor_type_id=constants.DISTRIBUTOR_TYPE_ID,
                 distributor_config=config,
                 auto_publish=auto_publish,
                 distributor_id=constants.CLI_DISTRIBUTOR_ID),
        ]

        return data

    def _parse_importer_config(self, user_input):
        """
        Subclasses should override this to provide whatever option parsing
        is needed to create an importer config.

        :param user_input:  dictionary of data passed in by okaara
        :type  user_input:  dict
        :return:            importer config
        :rtype:             dict
        """
        config = self.parse_user_input(user_input)
        if OPT_PACKAGE_NAMES.keyword in user_input:
            config[constants.CONFIG_KEY_PACKAGE_NAMES] = user_input.pop(OPT_PACKAGE_NAMES.keyword)
        return config


class CreateNpmRepositoryCommand(NpmRepositoryOptions, CreateAndConfigureRepositoryCommand,
                                 ImporterConfigMixin):
    """
    This CLI command is used to create Npm repositories on the server.
    """

    default_notes = {REPO_NOTE_TYPE_KEY: constants.REPO_NOTE_NPM}
    IMPORTER_TYPE_ID = constants.IMPORTER_TYPE_ID

    def __init__(self, context):
        """
        Initialize the create command.

        :param context: The CLI context
        :type  context: pulp.client.extensions.core.ClientContext
        """
        CreateAndConfigureRepositoryCommand.__init__(self, context)
        ImporterConfigMixin.__init__(self, **IMPORTER_CONFIGURATION_FLAGS)
        NpmRepositoryOptions.__init__(self)


class UpdateNpmRepositoryCommand(NpmRepositoryOptions, UpdateRepositoryCommand,
                                 ImporterConfigMixin):
    """
    This CLI command allows the user to update existing Npm repositories.
    """

    def __init__(self, context):
        """
        Initialize the update command.

        :param context: The CLI context
        :type  context: pulp.client.extensions.core.ClientContext
        """
        UpdateRepositoryCommand.__init__(self, context)
        ImporterConfigMixin.__init__(self, **IMPORTER_CONFIGURATION_FLAGS)
        NpmRepositoryOptions.__init__(self)

    def run(self, **kwargs):
        """
        Perform the update on the server.

        :param kwargs: The user input
        :type  kwargs: dict
        """
        arg_utils.convert_removed_options(kwargs)

        importer_config = self._parse_importer_config(kwargs)

        # Remove importer specific keys
        for key in importer_config:
            kwargs.pop(key, None)

        if importer_config:
            kwargs['importer_config'] = importer_config

        # Update distributor configuration
        web_config = {}
        value = kwargs.pop(OPT_AUTO_PUBLISH.keyword, None)
        if value is not None:
            web_config['auto_publish'] = value

        if web_config:
            kwargs['distributor_configs'] = {}
            kwargs['distributor_configs'][constants.CLI_DISTRIBUTOR_ID] = web_config

        super(UpdateNpmRepositoryCommand, self).run(**kwargs)


class ListNpmRepositoriesCommand(ListRepositoriesCommand):
    """
    This CLI command presents the user with the list of Npm repositories that exist on the
    server.
    """

    def __init__(self, context):
        """
        Initialize the list command.

        :param context: The CLI context
        :type  context: pulp.client.extensions.core.ClientContext
        """
        repos_title = _('Npm Repositories')
        super(ListNpmRepositoriesCommand, self).__init__(context, repos_title=repos_title)

        # Both get_repositories and get_other_repositories will act on the full
        # list of repositories. Lazy cache the data here since both will be
        # called in succession, saving the round trip to the server.
        self.all_repos_cache = None

    def get_repositories(self, query_params, **kwargs):
        """
        Get a list of all the Npm repositories that match the specified query params

        :param query_params: query parameters for refining the list of repositories
        :type  query_params: dict
        :param kwargs:       Any additional parameters passed into the repo list command
        :type  kwargs:       dict
        :return:             List of Npm repositories
        :rtype:              list of dict
        """
        all_repos = self._all_repos(query_params, **kwargs)

        npm_repos = []
        for repo in all_repos:
            notes = repo['notes']
            if REPO_NOTE_TYPE_KEY in notes \
                    and notes[REPO_NOTE_TYPE_KEY] == constants.REPO_NOTE_NPM:
                npm_repos.append(repo)

        return npm_repos

    def get_other_repositories(self, query_params, **kwargs):
        """
         Get a list of all the non npm repositories that match the specified query params

        :param query_params: query parameters for refining the list of repositories
        :type  query_params: dict
        :param kwargs:       Any additional parameters passed into the repo list command
        :type  kwargs:       dict
        :return:             List of non repositories
        :rtype:              list of dict
        """
        all_repos = self._all_repos(query_params, **kwargs)

        non_npm_repos = []
        for repo in all_repos:
            notes = repo['notes']
            if notes.get(REPO_NOTE_TYPE_KEY, None) != constants.REPO_NOTE_NPM:
                non_npm_repos.append(repo)

        return non_npm_repos

    def _all_repos(self, query_params, **kwargs):
        """
        get all the repositories associated with a repo that match a set of query parameters

        :param query_params: query parameters for refining the list of repositories
        :type  query_params: dict
        :param kwargs:       Any additional parameters passed into the repo list command
        :type  kwargs:       dict
        :return:             list of repositories
        :rtype:              list of dict
        """
        # This is safe from any issues with concurrency due to how the CLI works
        if self.all_repos_cache is None:
            self.all_repos_cache = self.context.server.repo.repositories(query_params).response_body

        return self.all_repos_cache
