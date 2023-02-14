#!/usr/bin/env

__author__ = "Florian Hase"

# ========================================================================

import json

# ========================================================================


class ParserJSON(object):
    def __init__(self, json_file=None):
        self.json_file = json_file

    def parse(self, json_file=None):
        # update json file
        if json_file is not None:
            self.json_file = json_file

        # parse configuration
        if self.json_file is not None:
            with open(self.json_file) as content:
                self.parsed_json = json.loads(content.read())
        else:
            from utilities.defaults import default_configuration

            self.parsed_json = default_configuration
        return self.parsed_json
