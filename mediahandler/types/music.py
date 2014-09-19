#!/usr/bin/python
#
# This file is a part of EM Media Handler
# Copyright (c) 2014 Erin Morelli
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.


# ======== IMPORT MODULES ======== #

import re
import logging
from os import path, makedirs
from subprocess import Popen, PIPE


# ======== CLASS DECLARTION ======== #

class Music:

    # ======== INIT MUSIC CLASS ======== #

    def __init__(self, settings):
        logging.info("Initializing renaming class")
        # Beet Options
        self.beet = "/usr/local/bin/beet"
        self.beetslog = '%s/logs/beets.log' % path.expanduser("~")
        # Check for custom path in settings
        if settings['log_file'] != '':
            self.beetslog = settings['log_file']
            logging.debug("Using custom beets log: %s" % self.beetslog)
        # Check that log file path exists
        beetslog_dir = path.dirname(self.beetslog)
        if not path.exists(beetslog_dir):
            makedirs(beetslog_dir)

    # ======== ADD MUSIC ======== #

    def add_music(self, file_path, is_single=False):
        logging.info("Starting music information handler")
        # Set Variables
        if is_single:
            m_type = "Song"
            m_tags = "-sql"
            m_query = "Tagging track\:\s(.*)\nURL\:\n\s{1,4}(.*)\n"
        else:
            m_type = "Album"
            m_tags = "-ql"
            m_query = "(Tagging|To)\:\n\s{1,4}(.*)\nURL\:\n\s{1,4}(.*)\n"
        # Set up query
        m_cmd = [self.beet,
                "import", file_path,
                m_tags, self.beetslog]
        logging.debug("Query: %s", m_cmd)
        # Process query
        p = Popen(m_cmd, stdout=PIPE, stderr=PIPE)
        # Get output
        (output, err) = p.communicate()
        logging.debug("Query output: %s", output)
        logging.debug("Query return errors: %s", err)
        # Process output
        if err != '':
            return None
        # Check for skip
        if re.search(r"(Skipping\.)\n", output):
            logging.warning("Beets is skipping the import: %s" % output)
            return None
        # Extract Info
        music_find = re.compile(m_query)
        logging.debug("Search query: %s", m_query)
        # Format data
        music_data = music_find.search(output)
        music_info = "%s: %s" % (m_type, music_data.group(2))
        logging.info("MusicBrainz URL: %s" % music_data.group(3))
        # Return music data
        return music_info
