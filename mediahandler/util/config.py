#!/usr/bin/python
#
# This file is a part of EM Media Handler
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
'''Configuration file handler'''


# ======== IMPORT MODULES ======== #

import os
import imp
import yaml
import shutil
import logging

import mediahandler as mh
import mediahandler.util as util


# ======== LOOK FOR MODULE ======== #

def _find_module(parent_mod, sub_mod):
    '''Look to see if module is installed'''
    try:
        mod_info = imp.find_module(parent_mod)
        mod = imp.load_module(parent_mod, *mod_info)
        imp.find_module(sub_mod, mod.__path__)
        return True
    except ImportError:
        err_msg = 'Module %s.%s is not installed' % (parent_mod, sub_mod)
        raise ImportError(err_msg)


# ======== LOGGING ======== #

def init_logging(settings):
    '''Turn on logging'''
    # Set defaults
    log_file = '%s/logs/mediahandler.log' % os.path.expanduser("~")
    log_level = 30
    # Look for exceptions
    if settings['Logging']['log_file'] is not None:
        log_file = settings['Logging']['log_file']
    if settings['Logging']['level'] is not None:
        log_level = settings['Logging']['level']
    # Make sure log file dir exists
    log_path = os.path.dirname(log_file)
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    # Config logging
    logging.basicConfig(
        filename=log_file,
        format='%(asctime)s - %(filename)s - %(levelname)s - %(message)s',
        level=log_level,
    )
    # Enable deluge logging
    if settings['Deluge']['enabled']:
        from deluge.log import setupLogger
        setupLogger()
    return


# ======== CHECK MODULES ======== #

def _check_modules(settings):
    '''Check that needed modules are installed'''
    # Check for logging
    if settings['Logging']['enabled']:
        init_logging(settings)
        logging.info('Logging enabled')
    # Check for requirements
    require = _get_yaml('%s/require.yml' % mh.__mediaextras__)
    for section in require:
        item = require[section]
        option = item['option']
        if settings[section][option]:
            # Check modules
            if 'modules' in item.keys():
                for module in item['modules']:
                    _find_module(module[0], module[1])
            # Check applications
            if 'apps' in item.keys():
                # Save in settings
                name = 'has_%s' % item['apps']['name'].lower()
                settings[section][name] = None
                # Look for app
                for path in item['apps']['paths']:
                    if os.path.isfile(path):
                        settings[section][name] = path
                        break
                if settings[section][name] is None:
                    error = '%s application not found' % item['apps']['name']
                    raise ImportError(error)
    return


# ======== GET FILE STRUCTURE ======== #

def _get_yaml(yaml_file):
    '''Retrieve config structure from yaml file'''
    # Read yaml file
    yaml_contents = open(yaml_file).read()
    # Return decoded yaml
    return yaml.load(yaml_contents)


# ======== PARSE CONFIG FILE ======== #

def parse_config(file_path):
    '''Read config file'''
    # Read yaml files
    parsed = _get_yaml(file_path)
    struct = _get_yaml('%s/settings.yml' % mh.__mediaextras__)
    # Loop through config & validate
    settings = {}
    for item in struct['items']:
        section = item['section']
        # Loop through options
        new_options = {}
        for item_option in item['options']:
            option = item_option['name']
            value = ''
            # If option exists, get value
            if option in parsed[section].keys():
                value = parsed[section][option]
            # Otherwise use default
            elif 'default' in item_option.keys():
                value = item_option['default']
            # Fallback to non
            else:
                new_options[option] = None
                continue
            # Validate values
            valid_func = "_get_valid_%s" % item_option['type']
            validator = getattr(util.config, valid_func)
            new_options[option] = validator(section, option, value)
        # Populate hash
        settings[section] = new_options
    # Check that appropriate modules are installed
    _check_modules(settings)
    # Return setting hash
    return settings


# ======== VALIDATION ======== #

# BOOLEAN
def _get_valid_bool(section, option, provided):
    '''Validate config option as a boolean'''
    if provided is None:
        return False
    if type(provided) is not bool:
        error = ("Value provided for '%s: %s' is not a valid boolean"
                 % (section, option))
        raise ValueError(error)
    return provided


# STRING
def _get_valid_string(section, option, provided):
    '''Validate config option as a string'''
    if provided is None:
        return None
    if type(provided) is not str:
        error = ("Value provided for '%s: %s' is not a valid string"
                 % (section, option))
        raise ValueError(error)
    return provided


# NUMBER (INT)
def _get_valid_number(section, option, provided):
    '''Validate config option as an int'''
    if provided is None:
        return None
    try:
        return int(provided)
    except ValueError:
        error = ("Value provided for '%s: %s' is not a valid number"
                 % (section, option))
        raise ValueError(error)


# PATH TO FILE
def _get_valid_file(section, option, provided):
    '''Validate config option as a filepath'''
    if provided is None:
        return None
    folder = os.path.dirname(provided)
    if not os.path.exists(folder):
        error = ("Path to file provided for '%s: %s' does not exist: %s"
                 % (section, option, folder))
        raise ValueError(error)
    return provided


# FOLDER
def _get_valid_folder(section, option, provided):
    '''Validate config option as a folder'''
    if provided is None:
        return None
    if not os.path.exists(provided):
        error = ("Path provided for '%s: %s' does not exist: %s"
                 % (section, option, provided))
        raise ValueError(error)
    return provided


# ======== MAKE CONFIG FILE ======== #

def make_config(new_file=None):
    '''Generate default config file'''
    # Set default path
    config_file = ('%s/.config/mediahandler/config.yml' %
                   os.path.expanduser("~"))
    # Check for user-provided path
    if new_file is not None:
        config_file = new_file
    # Check that config exists
    if os.path.isfile(config_file):
        # Check config file permissions
        if not os.access(config_file, os.R_OK):
            raise Warning('Configuration file cannot be opened')
    else:
        # Copy default config to user file
        default_config = '%s/config.yml' % mh.__mediaextras__
        # Make directories for config file
        config_path = os.path.dirname(config_file)
        if not os.path.exists(config_path):
            os.makedirs(config_path)
            os.chmod(config_path, 0o775)
        # Copy new configuration file to path
        shutil.copy(default_config, config_file)
        # Change permissions to current user if sudo
        if 'SUDO_UID' in os.environ.keys():
            filed = os.open(config_file, os.O_RDONLY)
            os.fchown(filed, int(os.environ['SUDO_UID']), -1)
            os.close(filed)
    # Return with path to file
    return config_file
