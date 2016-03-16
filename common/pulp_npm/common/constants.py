PACKAGE_TYPE_ID = 'npm_package'
REPO_NOTE_NPM = 'npm'

IMPORTER_TYPE_ID = 'npm_importer'
DISTRIBUTOR_TYPE_ID = 'npm_distributor'

CLI_DISTRIBUTOR_ID = 'cli_npm_distributor'

DISTRIBUTOR_CONFIG_FILE_NAME = 'server/plugins.conf.d/npm_distributor.json'

# Config keys for the distributor plugin conf
CONFIG_KEY_PUBLISH_DIRECTORY = 'npm_publish_directory'
CONFIG_VALUE_PUBLISH_DIRECTORY = '/var/lib/pulp/published/npm'

CONFIG_KEY_PUBLISH_DOMAIN = 'npm_publish_domain'
CONFIG_VALUE_PUBLISH_DOMAIN = 'localhost'

# Config keys for the importer plugin conf
CONFIG_KEY_PACKAGE_NAMES = 'package_names'

# STEP_ID
PUBLISH_STEP_PUBLISHER = 'npm_publish_step'
PUBLISH_STEP_CONTENT = 'npm_publish_content'
PUBLISH_STEP_METADATA = 'npm_publish_metadata'
PUBLISH_STEP_OVER_HTTP = 'npm_publish_over_http'
