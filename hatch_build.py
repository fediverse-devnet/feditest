#
# Set a dynamic version number, see https://hatch.pypa.io/dev/how-to/config/dynamic-metadata/
# At release time, override with env var: FEDITEST_RELEASE_VERSION=y 
#

from datetime import datetime
import os

from hatchling.metadata.plugin.interface import MetadataHookInterface


class JSONMetaDataHook(MetadataHookInterface):
    def update(self, metadata):
        if 'FEDITEST_RELEASE_VERSION' in os.environ and os.environ['FEDITEST_RELEASE_VERSION'].lower() == 'y':
            metadata['version'] = metadata['base_version']
        else:
            metadata['version'] = metadata['base_version'] + '.dev' + datetime.now().strftime("%Y%m%d%H%M%S")
