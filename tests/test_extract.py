#!/usr/bin/python
#
# This file is a part of EM Media Handler Testing Module
# Copyright (c) 2014-2015 Erin Morelli
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
'''Initialize module'''

import os
import sys
import shutil
import zipfile

import _common
from _common import unittest
from _common import tempfile

import mediahandler.util.extract as Extract
import mediahandler.handler as MH


class ExtractBadZipTests(unittest.TestCase):

    def setUp(self):
        # Conf
        self.conf = _common.get_conf_file()
        # Tmp name
        self.name = "test-%s" % _common.get_test_id()
         # Tmp args
        args = { 'name': self.name }
        # Make handler
        self.handler = MH.Handler(args)
        # Bad zip non without extension
        get_bad_non_zip = tempfile.NamedTemporaryFile(
            dir=os.path.dirname(self.conf),
            suffix='.tmp',
            delete=False
        )
        self.bad_non_zip = get_bad_non_zip.name
        get_bad_non_zip.close()
        # Bad zip non with extension
        get_bad_zip = tempfile.NamedTemporaryFile(
            dir=os.path.dirname(self.conf),
            suffix='.zip',
            delete=False
        )
        self.bad_zip = get_bad_zip.name
        get_bad_zip.close()

    def tearDown(self):
        os.unlink(self.bad_zip)
        os.unlink(self.bad_non_zip)

    def test_bad_zip(self):
        self.assertIsNone(Extract.get_files(self.bad_zip))
    
    def test_bad_non_zip(self):
        self.assertIsNone(Extract.get_files(self.bad_non_zip))

    def test_bad_handler_zip(self):
        # Run handler
        regex = r'Unable to extract files: %s' % self.name
        self.assertRaisesRegexp(
            SystemExit, regex,
            self.handler.extract_files, self.bad_zip
        )

    def test_bad_handler_non_zip(self):
        # Run handler
        regex = r'Unable to extract files: %s' % self.name
        self.assertRaisesRegexp(
            SystemExit, regex,
            self.handler.extract_files, self.bad_non_zip
        )


class ExtractGoodZipTests(unittest.TestCase):

    def setUp(self):
        # Conf
        self.conf = _common.get_conf_file()
        # Tmp name
        self.name = "test-%s" % _common.get_test_id()
        # Tmp args
        args = {
            'name': self.name,
            'type': 1,
            'stype': 'TV'
        }
        # Make handler
        self.handler = MH.Handler(args)
        # Make a good zip file contents
        get_good_zip1 = tempfile.NamedTemporaryFile(
            suffix='.tmp',
            delete=False
        )
        get_good_zip2 = tempfile.NamedTemporaryFile(
            suffix='.tmp',
            delete=False
        )
        self.good_zip1 = get_good_zip1.name
        self.good_zip2 = get_good_zip2.name
        get_good_zip1.close()
        get_good_zip2.close()
        # Make zip file
        self.zip_name = os.path.dirname(self.conf) + "/test_ET.zip"
        with zipfile.ZipFile(self.zip_name, "w") as good_zip:
            good_zip.write(self.good_zip1, 'one.tmp')
            good_zip.write(self.good_zip2, 'two.tmp')

    def tearDown(self):
        os.unlink(self.good_zip1)
        os.unlink(self.good_zip2)
        os.unlink(self.zip_name)
        # Remove extracted files
        folder = '%s/test_ET' % os.path.dirname(self.conf)
        shutil.rmtree(folder)

    def test_good_extract(self):
        files = Extract.get_files(self.zip_name)
        folder = '%s/test_ET' % os.path.dirname(self.conf)
        self.assertEqual(files, folder)
        self.assertTrue(os.path.exists(files))

    def test_good_handler_zip(self):
        # Run handler
        files = self.handler.extract_files(self.zip_name)
        folder = '%s/test_ET' % os.path.dirname(self.conf)
        self.assertEqual(files, folder)
        self.assertTrue(os.path.exists(files))
        self.assertEqual(self.handler.settings['extracted'], self.zip_name)

    def test_good_handler_zip_found(self):
        # Run handler
        regex = r'Folder for TV not found: .*/Media/TV'
        self.assertRaisesRegexp(
            SystemExit, regex, self.handler._find_zipped, self.zip_name)


def suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
