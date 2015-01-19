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
from mutagen.mp3 import MP3

import _common
from _common import unittest
from _common import MHTestSuite

from test_media import MediaObjectTests

import mediahandler.types.audiobooks as Books


class BookMediaObjectTests(MediaObjectTests):

    def setUp(self):
        # Call Super
        super(BookMediaObjectTests, self).setUp()
        # Real audio file for testing
        self.audio_file = os.path.join(
            os.path.dirname(__file__), 'extra', 'test_mp3_file.mp3')
        # Book-specific settings
        self.settings['api_key'] = _common.get_google_api()
        self.settings['chapter_length'] = None
        self.settings['make_chapters'] = False
        # Make an object
        self.book = Books.Book(self.settings, self.push)


class BaseBookObjectTests(BookMediaObjectTests):

    def test_bad_google_api(self):
        self.settings['api_key'] = None
        regex = r'Google Books API key not found'
        self.assertRaisesRegexp(
            Warning, regex, Books.Book, self.settings, self.push)

    def test_custom_chapter_length(self):
        self.settings['chapter_length'] = 10
        self.book = Books.Book(self.settings, self.push)
        self.assertEqual(self.book.settings['max_length'], 36000)

    def test_custom_search_string(self):
        search = 'Gone Girl Gillian Flynn'
        self.settings['custom_search'] = search
        self.book = Books.Book(self.settings, self.push)
        self.assertEqual(self.book.settings['custom_search'], search)


class BookCleanStringTests(BookMediaObjectTests):

    def test_blacklist_string(self):
        string = os.path.join(self.folder, 'Yes Please iTunes Audiobook Unabridged')
        expected = 'Yes Please'
        self.assertEqual(self.book._clean_string(string), expected)

    def test_bracket_string(self):
        string = os.path.join(self.folder, 'The Lovely Bones [A Novel] (Mp3) {TKP}')
        expected = 'The Lovely Bones'
        self.assertEqual(self.book._clean_string(string), expected)

    def test_non_alphanum_string(self):
        string = os.path.join(self.folder, 'Jar City - A Novel - 2000')
        expected = 'Jar City A Novel'
        self.assertEqual(self.book._clean_string(string), expected)

    def test_whitespace_string(self):
        string = os.path.join(self.folder, 'The   Goldfinch  ')
        expected = 'The Goldfinch'
        self.assertEqual(self.book._clean_string(string), expected)

    def test_extras_string(self):
        string = os.path.join(self.folder, 'Black Skies CPK MP3 ENG YIFY')
        expected = 'Black Skies'
        self.assertEqual(self.book._clean_string(string), expected)


class BookSaveCoverTests(BookMediaObjectTests):

    def test_save_cover_new(self):
        img_url = 'http://books.google.com/books/content?id=4lYZAwAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api'
        expected = os.path.join(self.folder, 'cover.jpg')
        self.assertFalse(os.path.exists(expected))
        result = self.book._save_cover(self.folder, img_url)
        self.assertEqual(result, expected)
        self.assertEqual(self.book.book_info['cover_image'], expected)
        self.assertTrue(os.path.exists(expected))

    def test_save_cover_exists(self):
        img_url = 'http://books.google.com/books/content?id=4lYZAwAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api'
        expected = os.path.join(self.folder, 'cover.jpg')
        # Make file
        with open(expected, 'w'):
            pass
        # Run test
        self.assertTrue(os.path.exists(expected))
        result = self.book._save_cover(self.folder, img_url)
        self.assertEqual(result, expected)
        self.assertNotIn('cover_image', self.book.book_info.keys())


class BookCalculateChunkTests(BookMediaObjectTests):

    def test_chunks_mulipart(self):
        # Set max length to 30 mins
        self.book.settings['max_length'] = 1800
        # Copy files into folder
        for x in range(0, 6):
            dst = os.path.join(self.folder, '0{0}-track.mp3'.format(str(x+1)))
            shutil.copy(self.audio_file, dst)
        # Set up query
        file_array = sorted(os.listdir(self.folder))
        expected = [
            ['01-track.mp3', '02-track.mp3'],
            ['03-track.mp3', '04-track.mp3'],
            ['05-track.mp3', '06-track.mp3']
        ]
        # Run test
        result = self.book._calculate_chunks(self.folder, file_array, 'mp3')
        # Check results
        self.assertEqual(len(result), 3)
        self.assertListEqual(result, expected)

    def test_chunks_single(self):
        # Set max length to 15 mins
        self.book.settings['max_length'] = 900
        # Copy file into folder
        dst = os.path.join(self.folder, '01-track.mp3')
        shutil.copy(self.audio_file, dst)
        # Set up query
        file_array = sorted(os.listdir(self.folder))
        expected = [['01-track.mp3']]
        # Run test
        result = self.book._calculate_chunks(self.folder, file_array, 'mp3')
        # Check results
        self.assertEqual(len(result), 1)
        self.assertListEqual(result, expected)

    def test_chunks_single_parts(self):
        # Set max length to 10 mins
        self.book.settings['max_length'] = 600
        # Copy file into folder
        dst = os.path.join(self.folder, '01-track.mp3')
        shutil.copy(self.audio_file, dst)
        # Set up query
        file_array = sorted(os.listdir(self.folder))
        expected = [['01-track.mp3']]
        # Run test
        result = self.book._calculate_chunks(self.folder, file_array, 'mp3')
        # Check results
        self.assertEqual(len(result), 1)
        self.assertListEqual(result, expected)


class GetChaptersTests(BookMediaObjectTests):

    def make_cover(self):
        # Make dummy cover image
        tmp_img = _common.make_tmp_file('.jpg')
        cover_img = os.path.join(self.folder, 'cover.jpg')
        shutil.move(tmp_img, cover_img)

    def test_chapters_mulipart(self):
        # Set max length to 30 mins
        self.book.settings['max_length'] = 1800
        # Copy files into folder
        for x in range(0, 6):
            dst = os.path.join(self.folder, '0{0}-track.mp3'.format(str(x+1)))
            shutil.copy(self.audio_file, dst)
        # Set up query
        file_array = sorted(os.listdir(self.folder))
        # Make cover
        self.make_cover()
        expected = [
            os.path.join(self.folder, 'Part 1'),
            os.path.join(self.folder, 'Part 2'),
            os.path.join(self.folder, 'Part 3'),
        ]
        # Run test
        result = self.book._get_chapters(self.folder, file_array, 'mp3')
        # Check results
        self.assertEqual(len(result), 3)
        self.assertListEqual(result, expected)

    def test_chunks_single(self):
        # Set max length to 15 mins
        self.book.settings['max_length'] = 900
        # Copy file into folder
        dst = os.path.join(self.folder, '01-track.mp3')
        shutil.copy(self.audio_file, dst)
        # Set up query
        file_array = sorted(os.listdir(self.folder))
        # Make cover
        self.make_cover()
        expected = [os.path.join(self.folder, 'Part 1')]
        # Run test
        result = self.book._get_chapters(self.folder, file_array, 'mp3')
        # Check results
        self.assertEqual(len(result), 1)
        self.assertListEqual(result, expected)


@unittest.skipUnless(sys.platform.startswith("linux"), "requires Ubuntu")
class AddBookTest(BookMediaObjectTests):
    
    def test_add_book(self):
        # Set up abc path
        self.book.settings['has_abc'] = os.path.join('/', 'usr', 'local', 'bin', 'abc.php')
        if not os.path.exists(self.book.settings['has_abc']):
            self.book.settings['has_abc'] = os.path.join('/', 'usr', 'bin', 'abc.php')
        # Set max length to 30 mins
        self.book.settings['max_length'] = 1800
        self.book.settings['make_chapters'] = True
        self.book.settings['custom_search'] = 'Paul Doiron Bone Orchard'
        # Copy files into folder
        for x in range(0, 2):
            dst = os.path.join(self.folder, '0{0}-track.mp3'.format(str(x+1)))
            shutil.copy(self.audio_file, dst)
        # Run test
        (result, skips) = self.book.add(self.folder)
        # Check results
        regex = r'"The Bone Orchard: A Novel" by Paul Doiron'
        self.assertRegexpMatches(result, regex)
        self.assertFalse(skips)
        # Check that file was made
        created = os.path.join(self.folder, 'Paul Doiron',
            'The Bone Orchard_ A Novel', 'The Bone Orchard.m4b')
        self.assertTrue(os.path.exists(created))


class GetFilesTests(BookMediaObjectTests):

    def test_get_files_mixed(self):
        # Set up folder
        book_file1 = _common.make_tmp_file('.m4b', self.folder)
        book_file2 = _common.make_tmp_file('.m4b', self.folder)
        book_file3 = _common.make_tmp_file('.mp3', self.folder)
        # Set up test
        expected = [book_file1, book_file2]
        # Run test
        (success, result) = self.book._get_files(self.folder, False)
        # Check results
        self.assertTrue(success)
        self.assertListEqual(sorted(expected), sorted(result))

    def test_get_files_good(self):
        # Set up folder
        book_file1 = _common.make_tmp_file('.m4b', self.folder)
        book_file2 = _common.make_tmp_file('.m4b', self.folder)
        # Set up test
        expected = [book_file1, book_file2]
        # Run test
        (success, result) = self.book._get_files(self.folder, False)
        # Check results
        self.assertTrue(success)
        self.assertListEqual(sorted(expected), sorted(result))

    def test_get_files_bad(self):
        # Set up folder
        book_file1 = _common.make_tmp_file('.mp3', self.folder)
        book_file2 = _common.make_tmp_file('.mp3', self.folder)
        # Set up test
        expected = [
            os.path.basename(book_file1),
            os.path.basename(book_file2)
        ]
        # Run test
        (success, result) = self.book._get_files(self.folder, False)
        # Check results
        self.assertTrue(success)
        self.assertListEqual(sorted(expected), sorted(result))
        self.assertEqual(self.book.settings['file_type'], 'mp3')

    @_common.skipUnlessHasMod('mutagen', 'mp3')
    def test_get_files_bad_chaptered(self):
        # Set up folder
        book_file1 = _common.make_tmp_file('.mp3', self.folder)
        book_file2 = _common.make_tmp_file('.mp3', self.folder)
        # Set up test
        import mutagen.mp3
        # Run test
        regex = r''
        self.assertRaisesRegexp(mutagen.mp3.HeaderNotFoundError,
            regex, self.book._get_files, self.folder, True)

    def test_get_files_none(self):
        # Set up folder
        book_file1 = _common.make_tmp_file('.m4a', self.folder)
        book_file2 = _common.make_tmp_file('.m4a', self.folder)
        # Set up test
        expected = []
        # Run test
        (success, result) = self.book._get_files(self.folder, False)
        # Check results
        self.assertFalse(success)
        self.assertListEqual(expected, result)


class MoveFilesBookTests(BookMediaObjectTests):

    def setUp(self):
        super(MoveFilesBookTests, self).setUp()
        # Set up book info
        new_book_info = self.book.ask_google('Outrage Arnaldur')
        self.book.book_info = new_book_info
        # Settings
        self.book.settings['orig_path'] = self.folder

    def test_move_no_subtitle(self):
        new_book_info = self.book.ask_google('The Lovely Bones Alice Sebold')
        self.book.book_info = new_book_info
         # Make dummy file
        book_file = _common.make_tmp_file('.m4b', self.folder)
        # Set up file array
        file_array = [book_file]
        # Run test
        (added, skipped) = self.book._move_files(file_array, True)
        # Check results
        expected = ['The Lovely Bones']
        new_file = os.path.join(self.folder,
            'Alice Sebold','The Lovely Bones', 'The Lovely Bones.m4b')
        self.assertListEqual(skipped, [])
        self.assertListEqual(expected, added)
        self.assertTrue(os.path.exists(new_file))

    def test_move_no_chapters(self):
        self.book.settings['file_type'] = 'mp3'
        # Make dummy files
        book_file1 = _common.make_tmp_file('.mp3', self.folder)
        book_file2 = _common.make_tmp_file('.mp3', self.folder)
        # Set up file array
        file_array = sorted(os.listdir(self.folder))
        # Run test
        (added, skipped) = self.book._move_files(file_array, False)
        # Check results
        expected = ['01 - Outrage.mp3', '02 - Outrage.mp3']
        self.assertListEqual(skipped, [])
        self.assertListEqual(expected, added)

    def test_move_chapters(self):
        # Make dummy files
        book_file1 = _common.make_tmp_file('.m4b', self.folder)
        book_file2 = _common.make_tmp_file('.m4b', self.folder)
        # Set up file array
        file_array =[book_file1, book_file2]
        # Run test
        (added, skipped) = self.book._move_files(file_array, True)
        # Set expected values
        expected = ['Outrage, Part 1', 'Outrage, Part 2']
        new_path = os.path.join(self.folder, 'Arnaldur Indridason',
            'Outrage_ An Inspector Erlendur Novel')
        new_file1 = os.path.join(new_path, 'Outrage, Part 1.m4b')
        new_file2 = os.path.join(new_path, 'Outrage, Part 2.m4b')
        # Check results
        self.assertListEqual(skipped, [])
        self.assertListEqual(expected, added)
        self.assertTrue(os.path.exists(new_file1))
        self.assertTrue(os.path.exists(new_file2))

    def test_move_duplicates(self):
        # Make existing files
        new_path = os.path.join(self.folder, 'Arnaldur Indridason',
            'Outrage_ An Inspector Erlendur Novel')
        new_file1 = os.path.join(new_path, 'Outrage, Part 1.m4b')
        new_file2 = os.path.join(new_path, 'Outrage, Part 2.m4b')
        dummy_file = _common.make_tmp_file('.m4b', self.folder)
        # Make directories & files
        os.makedirs(new_path)
        shutil.copy(dummy_file, new_file1)
        shutil.copy(dummy_file, new_file2)
        # Make dummy files
        book_file1 = _common.make_tmp_file('.m4b', self.folder)
        book_file2 = _common.make_tmp_file('.m4b', self.folder)
        # Set up file array
        file_array =[book_file1, book_file2]
        # Run test
        (added, skipped) = self.book._move_files(file_array, True)
        # Set expected values
        expected = [new_file1, new_file2]
        # Check results
        self.assertListEqual(added, [])
        self.assertListEqual(expected, skipped)


class SingleFileBookTests(BookMediaObjectTests):

    def test_single_file_good(self):
        # Set up test
        self.book.settings['orig_path'] = self.folder
        book_file = _common.make_tmp_file('.m4b', self.folder)
        # Run test
        result = self.book._single_file(book_file, 'The Lovely Bones')
        # Check results
        expected_path = os.path.join(self.folder, 'The Lovely Bones')
        expected_file = os.path.join(expected_path, os.path.basename(book_file))
        self.assertEqual(expected_path, result)
        self.assertTrue(os.path.exists(expected_file))

    def test_ask_google_return(self):
        # Run test
        result = self.book.ask_google('Voices Arnaldur')
        # Check result
        expected = {
            'author': 'Arnaldur Indridason',
            'cover': 'http://books.google.com/books/content?id=BDgMX4r2efUC&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api',
            'genre': 'Fiction',
            'id': 'BDgMX4r2efUC',
            'long_title': 'Voices: An Inspector Erlendur Novel',
            'short_title': 'Voices',
            'subtitle': 'An Inspector Erlendur Novel',
            'year': '2008'
        }
        self.assertDictEqual(expected, result)



def suite():
    s = MHTestSuite()
    tests = unittest.TestLoader().loadTestsFromName(__name__)
    s.addTest(tests)
    return s


if __name__ == '__main__':
    unittest.main(defaultTest='suite', verbosity=2, buffer=True)