#!/usr/bin/python
#
# EM MEDIA HANDLER
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

__version__ = '1.0'
__author__ = 'Erin Morelli <erin@erinmorelli.com>'


# ======== IMPORT MODULES ======== #

import sys, re, os
import shutil, logging, getopt
import config
import extras.notify as Notify

from os import path, listdir, makedirs


# ======== SET GLOBAL OPTIONS ======== #

typesList = ['TV', 'Television', 'Movies', 'Music', 'Books', 'Audiobooks']


# ======== COMMAND LINE USAGE ======== #

def __showUsage(code):
	usageText = '''
EM Media Handler v%s / by %s

Usage: 
	mediaHandler.py -f /path/to/file [..options]


Options:
	-f 	: (required) Set path to media files, assumes path structure /path/to/<media type>/<media name>
	-c 	: Set a custom config file path
	-t 	: Force a specific media type for processing


Media types:
	%s
	''' % (__version__, __author__, '\n\t'.join(typesList))
	# Output text
	print usageText
	# Exit program
	sys.exit(int(code))


# ======== MOVE VIDEO FILES ======== #

def __addVideo(src):
	logging.info("Moving file(s)")
	# Set metadata options
	metadata = {
		"TV" : __addEpisode,
		"Television" : __addEpisode,
		"Movies" : __addMovie,
	}
	# Get paths
	fileInfo = metadata[args['type']](src) 
	# Check for errors
	if fileInfo == None:
		return None
	# Extract info
	(newName, dst) = fileInfo
	logging.debug("Name: %s", newName)
	logging.debug("DST: %s", dst)
	# Check that new file exists
	if not path.isfile(dst):
		Push.Failure("File failed to move %s" % dst)
	# Return new file name
	return newName


# ======== TELEVISION ======== #

# GET EPISODE INFO
def __addEpisode(raw):
	logging.info("Getting TV episode information")
	# Check that TV is enabled
	if not settings['TV']['enabled']:
		Push.Failure("TV type is not enabled")
	# Import TV module
	import media.tv as TV
	# Send info to handler
	e = TV.Episode(settings['TV'])
	epInfo = e.getEpisode(raw)
	if epInfo == None:
		Push.Failure("Unable to match episode: %s" % raw)
	# Extract info
	(epTitle, newFile) = epInfo
	# return folder and file paths
	return epTitle, newFile


# ======== MOVIES ======== #

# GET MOVIE INFO
def __addMovie(raw):
	logging.info("Getting movie information")
	# Check that Movies are enabled
	if not settings['Movies']['enabled']:
		Push.Failure("Movies type is not enabled")
	# Import movie module
	import media.movies as Movies
	# Send info to handler
	m = Movies.Movie(settings['Movies'])
	movInfo = m.getMovie(raw)
	if movInfo == None:
		Push.Failure("Unable to match movie: %s" % raw)
	# Extract info
	(movTitle, newFile) = movInfo
	# return folder and file paths
	return movTitle, newFile


# ======== MUSIC ======== #

# ADD MUSIC TO COLLETION
def __addMusic(raw, isSingle=False):
	logging.info("Getting music information")
	# Check that Movies are enabled
	if not settings['Movies']['enabled']:
		Push.Failure("Movies type is not enabled")
	# Import music module
	import media.music as Music
	# Send info to handler
	m = Music.newMusic(settings['Music'])
	musicInfo = m.addMusic(raw, isSingle)
	if musicInfo == None:
		Push.Failure("Unable to match music: %s\n%s" % (raw, musicInfo))
	# return album info
	return musicInfo


# ======== AUDIOBOOKS ======== #

# GET BOOK INFO
def __addBook(raw):
	logging.info("Getting audiobook information")
	# Check that Movies are enabled
	if not settings['Audiobooks']['enabled']:
		logging.warning("Audiobooks type is not enabled")
		raise Warning("Audiobooks type is not enabled")
	# Import audiobooks module
	import media.audiobooks as Audiobooks
	# Send to handler
	b = Audiobooks.Book(settings['Audiobooks'])
	bookInfo = b.getBook(raw)
	if bookInfo == None:
		Push.Failure("Unable to match book: %s\n%s" % raw, bookInfo)
		return None
	# return book info
	return bookInfo


# ======== EXTRACTION FUNCTION ======== #

def __extractFiles(raw):
	logging.info("Extracting files from compressed file")
	# Import extract module
	import extras.extract as Extract
	# Send to handler
	extracted = Extract.getFiles(raw)
	if extracted == None:
		Push.Failure("Unable to extract files: %s" % raw)
		return None
	# Send files back to handler
	return extracted


# ======== MAIN FILE FUNCTION ======== #

def __fileHandler(files):
	logging.info("Starting files handler")
	addedFiles = []
	# Process books first
	if args['type'] == "Books" or args['type'] == "Audiobooks":
		addedFile = __addBook(files)
		addedFiles.append(addedFile)
	# Then check for folders/files
	elif path.isfile(files):
		# Single file, treat differently
		logging.debug("Proecessing as a single file")
		# Look for zipped file first
		if re.search(r".(zip|rar|7z)$", files, re.I):
			logging.debug("Zipped file type detected")
			# Send to extractor
			if settings['TV']['enabled'] or settings['Movies']['enabled']:
				getFiles = __extractFiles(src)
				# Check for failure
				if getFiles == None:
					return None
				# Rescan files
				__fileHandler(getFiles)
		# otherwise treat like other files
		if args['type'] == "Music":
			addedFile = __addMusic(files, True)
			addedFiles.append(addedFile)
		else: 
			# Set single file as source
			src = files
			# Move file
			videoInfo = __addVideo(src)
			# Check for problems 
			if videoInfo == None:
				return
			addedFile = videoInfo
			addedFiles.append(addedFile)
	else:
		# Otherwise process as folder
		logging.debug("Proecessing as a folder")
		if args['type'] == "Music":
			addedFile = __addMusic(files)
			addedFiles.append(addedFile)
		else: 
			# Get a list of files
			fileList = listdir(files)
			# Locate video file in folder
			for f in fileList:
				# Look for file types we want
				if re.search(r"\.(mkv|avi|m4v|mp4)$", f, re.I):
					# Set info
					fileName = f
					src = files+'/'+fileName
					# Move file
					videoInfo = __addVideo(src)
					# Check for problems 
					if videoInfo == None:
						return
					addedFile = videoInfo
					addedFiles.append(addedFile)
	# Remove old files
	if not settings['General']['keep_files']:
		if path.exists(files):
			logging.debug("Removing extra files")
			shutil.rmtree(files)
	# Send success notification
	Push.Success(addedFiles)
	# Finish
	return addedFiles


# ======== GET ARGUMENTS ======== #

def __getArguments():
	useDeluge = False
	# Parse args
	try:
		(optlist, args) = getopt.getopt(sys.argv[1:], 'f:c:t:')
	except getopt.GetoptError as err:
		print str(err)
		__showUsage(2)
	# Check for failure conditions
	if len(optlist) > 0 and len(args) > 0:
		__showUsage(2)
	if len(optlist) == 0 and len(args) == 0:
		__showUsage(2)
	# Check for deluge
	if len(args) == 3:
		# Treat like deluge
		useDeluge = True
		newArgs = {
			'hash' : args[0],
			'name' : args[1],
			'path' : args[2]
		}
	elif len(args) > 0:
		__showUsage(2)
	# Check for CLI
	if len(optlist) > 0:
		newArgs = {}
		f = False
		for o,a in optlist:
			if o == '-f':
				f = True
				newArgs['media'] = a 
			if o == '-c':
				newArgs['config'] = a 
			if o == '-t':
				if a not in typesList:
					raise Warning('Media type %s not recognized' % a)
				newArgs['type'] = a
		if not f:
			print 'option -f not specified'
			__showUsage(2)
	return useDeluge, newArgs


# ======== HANDLE CLI MEDIA ======== #

def __handleMedia():
	logging.info("Processing from command line")
	logging.debug("Inputs: %s", args)
	# Extract info from path
	parsePath = re.search(r"^((.*)?\/(.*))\/(.*)$", args['media'], re.I)
	if parsePath:
		args['path'] = parsePath.group(1)
		args['name'] = parsePath.group(4)
		# Look for custom type
		if 'type' not in args.keys():
			args['type'] = parsePath.group(3)
			if args['type'] not in typesList:
					Push.Failure('Media type %s not recognized' % args['type'])
		logging.debug("Detected: %s", args)
	else:
		# Notify about failure
		Push.Failure"No type or name specified for media")
	# Check that file was downloaded
	if path.exists(args['media']):
		# Send to handler
		newFiles = __fileHandler(args['media'])
	else:
		# There was a problem, no files found
		Push.Failure("No media files found")
	return newFiles


# ======== HANDLE DELUGE MEDIA ======== #

def __handleDeluge():
	logging.info("Processing from deluge")
	logging.debug("Inputs: %s", args)
	# Extract media type from path
	findType = re.search(r"^(.*)?\/(.*)$", args['path'], re.I)
	if findType:
		args['type'] = findType.group(2)
		logging.debug("Type detected: %s", args['type'])
	else:
		if settings['General']['deluge']:
			# Remove torrent
			import extras.torrent
			extras.torrent.removeTorrent(settings['General'], args['hash'])
		# Notify about failure
		Push.Failure("No type specified for download: %s" % args['name'])
	# Check that file was downloaded
	filePath = args['path']+"/"+args['name']
	if path.exists(filePath):
		if settings['General']['deluge']:
			# Remove torrent
			import extras.torrent
			extras.torrent.removeTorrent(settings['General'], args['hash'])
		# Send to handler
		newFiles = __fileHandler(filePath)
	else:
		# There was a problem, no files found
		Push.Failure("No downloaded files found: %s" % args['name'])
	return newFiles


# ======== MAIN FUNCTION WRAPPER ======== #

def main():
	# Get arguments
	global args
	(useDeluge, args) = __getArguments()
	# Set paths
	__configPath = '%s/.config/mediaHandler/mediaHandler.conf' % path.expanduser("~")
	# Check for user-specified config
	if 'config' in args.keys():
		__configPath = args['config']
	# Check that config exists
	if not os.path.isfile(__configPath):
		raise Warning('Configuration file does not exist')
	# Check config file permissions
	if not os.access(__configPath, os.R_OK):
		raise Warning('Configuration file cannot be opened')
	# Get settings from config
	global settings
	settings = config.getConfig(__configPath)
	# Set up notify instance
	global Push
	Push = Notify.Push(settings['Pushover'])
	# If deluge, start processor
	if useDeluge:
		newFiles = __handleDeluge()
	# Start main function
	else: 
		newFiles = __handleMedia()
	# Exit
	return newFiles


# ======== COMMAND LINE ======== #

if __name__=='__main__':
	addedFiles = main()
	if len(addedFiles) > 0:
		print "\nMedia successfully added!\n"
		for a in addedFiles:
			print "\t%s" % str(a)
		print "\n"
	else:
		raise Warning("No media added")
