#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import shutil
from datetime import datetime

from jsonpatch import make_patch
from ludobox.utils import json_serial # convert datetime

from werkzeug import secure_filename
from slugify import slugify
from jsonschema import validate, ValidationError

from ludobox.errors import LudoboxError
from ludobox.config import read_config

config = read_config()

with open(os.path.join(os.getcwd(), "model/schema.json")) as f :
    schema = json.load(f)

def get_resource_slug(data):
    """Get the slugified name of the game based on the data set"""
    try:
        slug = slugify(data["title"])
        # add language
        language = data["audience"]["language"]
        return "%s-%s"%(slug,language)
    except KeyError as e:
        # TODO more explicit error message
        message = "KeyError occured while "\
                  "writing game info file to path '{path}'. "\
                  "Impossible to access data['title'].".format(
                    path=data)
        raise LudoboxError(message)

def validate_game_data(data):
    """Validate game data based on existing data VS a JSON Schema"""
    return validate(data, schema)

# TODO test this function with different scenari: existant/inexistant/not
#   readable dir, info.json present/absent/not readable, with/without attached
#   file
def read_game_info(path):
    """
    Read all the info available about the game stored at the provided path.

    Arguments:
    path -- directory where the game info and data are stored

    Returns a dictionary containing the game data.

    >>> data = read_game_info("tests/functional/data/hackathon/borgia-le-jeu-malsain")
    >>> print(', '.join(data['audience']))
    adults
    >>> print(', '.join(data['authors']))
    René
    >>> print(', '.join(data['themes']['fr']))
    Médiéval, Salopard

    If anythin goes wrong raise a LudoboxError containing description of the
    error and advice for fixing it.

    >>> try:
    ...     data = read_game_info("stupid_path/no_game")
    ... except LudoboxError as e:
    ...     print(e.message)
    <No such file or directory> occured while reading game 'no_game' info file 'stupid_path/no_game/info.json'

    The game data can come from:
    *   the info.json file
    *   the attached files found in the dir
    *   somme are also computed from other data like a cleaned name suitable
        for url generation (slugified name)
    """
    # Load JSON from the description file of the game
    json_path = os.path.join(path, "info.json")
    try:
        with open(json_path, "r") as json_file:
            data = json.load(json_file)
    except IOError as e:
        # TODO Handle more precisely the error and provide an advice for
        #   solving the problem
        # Create a very explicit message to explain the problem
        message = "<{error}> occured while "\
                  "reading game '{game}' info file '{json}'".format(
                    error=e.strerror,
                    game=os.path.basename(path),
                    json=e.filename)
        raise LudoboxError(message)

    # validate data
    validate_game_data(data)

    # TODO Add some attachment info

    # Add permalink
    data["slug"] = get_resource_slug(data)

    return data

def create_game_path(game_path) :
    """Create the dir to store the game"""
    try:
        os.makedirs(game_path)
    except Exception as e:
        message = "<{error}> occured while "\
                  "writing game info file to path '{path}'."\
                  "Impossible to create "\
                  "directory '{game_path}'.".format(
                    error=e.strerror,
                    path=config['data_dir'],
                    game_path=os.path.abspath(game_path))
        raise LudoboxError(message)
    print "path created : %s"%game_path

def write_game(info, attachments, data_dir):
    """
    Write a JSON file description of a game according to the provided data and
    attachment files in a dedicated directory named after the game.

    Arguments:
    info -- a dictionnary storing all the information about the game. It
            exactly mimic the structure of the disired JSON file. The
            data["title"] must exist, no other verification is made to
            check it contains coherent structure or data.
    attachments -- list of files attached to the game (rules, images...).
    data_dir -- directory where all the game directories are stored i.e. where
                a directory named after the game will be created to store the
                JSON file. It must exist.

    Returns the path to the directory created to store the JSON file (it
    should be named after the game!).

    Raises a LudoboxError if anything goes wrong.

    the :func:`write_game_info()` and :func:`read_game_info()` function should
    work nicely together. Any file writen with the first should be readable by
    the second:
    """

    slugified_name = get_resource_slug(info)

    # Create a directory after the cleaned name of the game
    game_path = os.path.join(data_dir, slugified_name)
    create_game_path(game_path)

    # create JSON resource
    write_info_json(info, game_path)

    # Write the attached files
    if attachments:
        try :
            write_attachments(attachments, game_path)
        except LudoboxError as e:
            raise LudoboxError(str(e))

    return game_path

def clean_game(game_path):
    """Delete an existing rep containing data of a game"""
    if os.path.exists(game_path):
        shutil.rmtree(game_path, ignore_errors=True)

def write_info_json(info, game_path):
    """Write a JSON file based on valid resource data"""

    # validate game data
    try:
        validate_game_data(info)
    except ValidationError as e:
        print e
        # Cleanup anything previously created
        clean_game(game_path)
        raise ValidationError(e)

    # Convert the data to JSON into file
    content = json.dumps(info, sort_keys=True, indent=4, default=json_serial)
    json_path = os.path.join(game_path, "info.json")

    try:
        with open(json_path, "w") as json_file:
            json_file.write(content.encode('utf-8'))
    except IOError as e:
        # Cleanup anything previously created
        clean_game(game_path)

        # TODO Handle more explicit message
        message = "<{error}> occured while "\
                  "writing game info file to path '{path}'"\
                  "Impossible to write JSON file '{json}'.".format(
                    error=e.strerror,
                    path=game_path,
                    json=json_path)
        raise LudoboxError(message)

ALLOWED_EXTENSIONS = ["txt", "png", "jpg", "gif", "stl", "zip", "pdf"]

def allowed_file(filename):
    """Check for valid file extensions"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def write_attachments(attachments, game_path):
    """Write all files contains in attachements into game directory"""

    # Create a directory to store the uploaded files
    attachments_path = os.path.join(game_path, "files")
    try:
        if not os.path.exists(attachments_path):
            os.makedirs(attachments_path)
    except Exception as e:
        message = "<Error> occured while "\
                  "writing game info to path '{path}'. "\
                  "Impossible to create "\
                  "directory '{attachments_path}' to store the attached "\
                  "files.".format(
                    path=game_path,
                    attachments_path=os.path.abspath(attachments_path))
        print message
        raise LudoboxError(message)

    # Write all the files
    for f in attachments:
        file_clean_name = secure_filename(f.filename)

        # check if extension is allowed
        # TODO: check for more security issues ?
        if not allowed_file(file_clean_name):
            message = "<{error}> occured while "\
                      "writing. Impossible to save file"\
                      "'{file_clean_name}' because exstension is not allowed".format(
                        error="FileNotAllowed", # TODO create ValidationError
                        file_clean_name=file_clean_name)

            raise LudoboxError(message)

        file_path = os.path.join(attachments_path, file_clean_name)
        print file_path
        try:
            f.save(file_path)
        except Exception as e:
            message = "<{error}> occured while "\
                      "writing game info to path '{path}'."\
                      "Impossible to save file"\
                      "'{file_path}' in the attachment directory "\
                      "'{attachments_path}'.".format(
                        error=e.strerror,
                        path=data_dir,
                        file_path=os.path.abspath(file_path),
                        attachments_path=os.path.abspath(attachments_path))
            raise LudoboxError(message)

def get_games_index():
    """Loop through all and parse an index of available games"""
    info_files = []

    # loop through all folders
    for item in os.listdir(config["data_dir"]) :
        path = os.path.join(config["data_dir"],item)
        # get only folders
        if os.path.isdir(path):
            info_file = os.path.join(path, "info.json")
            # check if folder contains a info.json file
            if os.path.exists(info_file):
                info = read_game_info(path)
                wanted_keys = [
                    "title",
                    "description",
                    "slug",
                    "audience",
                    "content_type"
                    ]

                info_files.append({ k : info[k] for k in wanted_keys if k in info.keys() })

    sorted_info_files = sorted(info_files, key=lambda k: k['title'])
    return sorted_info_files

def update_game_info(game_path, new_game_info):
    """
    Update game info based on changes

    - create patch changes using JSON patch (RFC 6902)
    - store patch in an history array within the JSON file
    - replace info original content with updated content
    """

    original_info = read_game_info(game_path)

    # create patch
    patch = make_patch(new_game_info,original_info)

    if not len(list(patch)) :
        return original_info

    # if patch
    # parse an event
    event = {
        "patch" : patch,
        "ts" : datetime.now().isoformat()
    }

    # init history if empty
    if "history" not in new_game_info.keys():
        new_game_info["history"] = []

    # add event to history
    new_game_info["history"].append(event)

    # write updated game to file
    write_info_json(new_game_info, game_path )
    return new_game_info

def store_files(game_path, attachments):
    """
    Write files

    - attachments: files to be uploaded to the game folder
    - path
    """
    print attachments

    # Write the attached files
    if attachments:
        try :
            write_attachments(attachments, game_path)
        except LudoboxError as e:
            raise LudoboxError(str(e))

    return game_path

def delete_file(file_path):
    try:
        os.remove(file_path)
    except OSError:
        pass
    return file_path
