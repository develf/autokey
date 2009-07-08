# -*- coding: utf-8 -*-

# Copyright (C) 2008 Chris Dekter

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os.path, shutil, configobj, logging
import cPickle as pickle
import iomediator

_logger = logging.getLogger("config-manager")

CONFIG_FILE = os.path.expanduser("~/.config/autokey/autokey.bin")
CONFIG_FILE_BACKUP = CONFIG_FILE + '~'

DEFAULT_ABBR_FOLDER = "Imported Abbreviations"

IS_FIRST_RUN = "isFirstRun"
SERVICE_RUNNING = "serviceRunning"
MENU_TAKES_FOCUS = "menuTakesFocus"
SHOW_TRAY_ICON = "showTrayIcon"
SORT_BY_USAGE_COUNT = "sortByUsageCount"
DETECT_UNWANTED_ABBR = "detectUnwanted"
PROMPT_TO_SAVE = "promptToSave"
PREDICTIVE_LENGTH = "predictiveLength"
INPUT_SAVINGS = "inputSavings"
ENABLE_QT4_WORKAROUND = "enableQT4Workaround"
INTERFACE_TYPE = "interfaceType"

def get_config_manager(autoKeyApp):
    if os.path.exists(CONFIG_FILE):
        _logger.info("Loading config from existing file: " + CONFIG_FILE)
        pFile = open(CONFIG_FILE, 'r')
        settings, configManager = pickle.load(pFile)
        pFile.close()
        apply_settings(settings)
        configManager.app = autoKeyApp
        
        if len(configManager.globalHotkeys) == 2:
            _logger.info("Upgrading from config file without showPopupHotkey")
            configManager.showPopupHotkey = GlobalHotkey()
            configManager.showPopupHotkey.set_hotkey(["<ctrl>", "<shift>"], " ")
            configManager.showPopupHotkey.enabled = True
            configManager.globalHotkeys.append(configManager.showPopupHotkey)
        autoKeyApp.init_global_hotkeys(configManager)
        _logger.info("Successfully loaded configuration file")
        _logger.debug("Global settings: " + repr(ConfigurationManager.SETTINGS))
        return configManager
    else:
        _logger.info("No configuration file found - creating new one")
        _logger.debug("Global settings: " + repr(ConfigurationManager.SETTINGS))
        return ConfigurationManager(autoKeyApp)

def save_config(configManager):
    _logger.info("Persisting configuration") 
    configManager.configHotkey.set_closure(None)
    configManager.toggleServiceHotkey.set_closure(None)
    configManager.showPopupHotkey.set_closure(None)
    autoKeyApp = configManager.app
    configManager.app = None

    # Back up configuration if it exists
    if os.path.exists(CONFIG_FILE):
        _logger.info("Backing up existing config file")
        shutil.copy(CONFIG_FILE, CONFIG_FILE_BACKUP)
    try:
        outFile = open(CONFIG_FILE, "wb")
        pickle.dump([ConfigurationManager.SETTINGS, configManager], outFile)
    except PickleError, pe:
        shutil.copy(CONFIG_FILE_BACKUP, CONFIG_FILE)
        _logger.error("Error while saving configuration. Backup has been restored.")
        raise Exception("Error while saving configuration. Backup has been restored.")
    finally:
        outFile.close()
        autoKeyApp.init_global_hotkeys(configManager)
        configManager.app = autoKeyApp
        _logger.info("Finished persisting configuration - no errors")
    
def apply_settings(settings):
    """
    Allows new settings to be added without users having to lose all their configuration
    """
    for key, value in settings.iteritems():
        ConfigurationManager.SETTINGS[key] = value
        
def _chooseInterface():
    # Choose a sensible default interface type. Get Xorg version to determine this:
    try:
        f = open("/var/log/Xorg.0.log", "r")
        for x in range(2):
            versionLine = f.readline()
            if "X Server" in versionLine:
                break
        f.close()
        versionLine = versionLine.strip()
        version = versionLine.split(" ")[-1]
        minorVersion = version.split(".")[1]
    except:
        minorVersion = None
        
    if minorVersion is None:
        return iomediator.X_EVDEV_INTERFACE
    elif minorVersion < 6:
        return iomediator.X_RECORD_INTERFACE
    else:
        return iomediator.X_EVDEV_INTERFACE

class ImportException(Exception):
    """
    Exception raised when an error occurs during the import of an abbreviations file.
    """
    pass
    

class ConfigurationManager:
    """
    Contains all application configuration, and provides methods for updating and 
    maintaining consistency of the configuration. 
    """

    """
    Static member for global application settings.
    """
    SETTINGS = {
                IS_FIRST_RUN : True,
                SERVICE_RUNNING : True,
                MENU_TAKES_FOCUS : False,
                SHOW_TRAY_ICON : True,
                SORT_BY_USAGE_COUNT : True,
                DETECT_UNWANTED_ABBR : False,
                PROMPT_TO_SAVE: True,
                PREDICTIVE_LENGTH : 5,
                INPUT_SAVINGS : 0,
                ENABLE_QT4_WORKAROUND : False,
                INTERFACE_TYPE : _chooseInterface()
                }
    
    def __init__(self, app):
        """
        Create initial default configuration
        """ 
        self.app = app
        self.folders = {}
        self.configHotkey = GlobalHotkey()
        self.configHotkey.set_hotkey(["<ctrl>"], "k")
        self.configHotkey.enabled = True
        
        self.toggleServiceHotkey = GlobalHotkey()
        self.toggleServiceHotkey.set_hotkey(["<ctrl>", "<shift>"], "k")
        self.toggleServiceHotkey.enabled = True    
        
        self.showPopupHotkey = GlobalHotkey()
        self.showPopupHotkey.set_hotkey(["<ctrl>", "<shift>"], " ")
        self.showPopupHotkey.enabled = True
                
        # TODO TESTING REMOVE ME LATER
        from iomediator import Key
        myPhrases = PhraseFolder("My Phrases")
        myPhrases.set_hotkey(["<ctrl>"], "<f7>")
        myPhrases.set_modes([PhraseMode.HOTKEY])
        
        f = PhraseFolder("Addresses")
        adr = Phrase("Home Address", "22 Avenue Street\nBrisbane\nQLD\n4000")
        adr.set_modes([PhraseMode.ABBREVIATION])
        adr.set_abbreviation("adr")
        f.add_phrase(adr)
        myPhrases.add_folder(f)        

        p = Phrase("First phrase", "Test phrase number one!")
        p.set_modes([PhraseMode.PREDICTIVE])
        p.set_window_titles(".* - gedit")
        myPhrases.add_phrase(p)
        
        p1 = Phrase("Positioning Phrase", "[udc]$(cursor )[/udc]\nBlah")
        p1.set_modes([PhraseMode.ABBREVIATION, PhraseMode.HOTKEY])
        p1.set_hotkey(["<ctrl>"], 'j')
        p1.set_abbreviation("udc")
        p1.showInTrayMenu = True
        p1.immediate = True
        myPhrases.add_phrase(p1)
        
        myPhrases.add_phrase(Phrase("Second phrase", "Test phrase number two!"))
        myPhrases.add_phrase(Phrase("Third phrase", "Test phrase number three!"))
        self.folders[myPhrases.title] = myPhrases
        
        trayPhrases = PhraseFolder("Tray Phrases", showInTrayMenu=True)
        trayPhrases.add_phrase(Phrase("First phrase", "Test phrase number one!"))
        trayPhrases.add_phrase(Phrase("Second phrase", "Test phrase number two!"))
        trayPhrases.add_phrase(Phrase("Third phrase", "Test phrase number three!"))
        self.folders[trayPhrases.title] = trayPhrases
        
        self.config_altered()
            
    def config_altered(self):
        """
        Called when some element of configuration has been altered, to update
        the lists of phrases/folders. 
        """
        _logger.info("Configuration changed - rebuilding in-memory structures")
        # Rebuild root folder list
        rootFolders = self.folders.values()
        self.folders.clear()
        for folder in rootFolders:
            self.folders[folder.title] = folder
        
        self.hotKeyFolders = []
        self.hotKeyPhrases = []
        
        self.abbrPhrases = []
        
        self.allFolders = []
        self.allPhrases = []
        
        for folder in self.folders.values():
            if PhraseMode.HOTKEY in folder.modes:
                self.hotKeyFolders.append(folder)
            self.allFolders.append(folder)
            
            self.__processFolder(folder)
        
        self.globalHotkeys = []
        self.globalHotkeys.append(self.configHotkey)
        self.globalHotkeys.append(self.toggleServiceHotkey)
        self.globalHotkeys.append(self.showPopupHotkey)
        _logger.debug("Global hotkeys: " + repr(self.globalHotkeys))
        
        _logger.debug("Hotkey folders: " + repr(self.hotKeyFolders))
        _logger.debug("Hotkey phrases: " + repr(self.hotKeyPhrases))
        _logger.debug("Abbreviation phrases: " + repr(self.abbrPhrases))
        _logger.debug("All folders: " + repr(self.allFolders))
        _logger.debug("All phrases: " + repr(self.allPhrases))
        
        save_config(self)
                    
    def __processFolder(self, parentFolder):
        for folder in parentFolder.folders:
            if PhraseMode.HOTKEY in folder.modes:
                self.hotKeyFolders.append(folder)
            self.allFolders.append(folder)
            
            self.__processFolder(folder)
            
        for phrase in parentFolder.phrases:
            if PhraseMode.HOTKEY in phrase.modes:
                self.hotKeyPhrases.append(phrase)
            if PhraseMode.ABBREVIATION in phrase.modes:
                self.abbrPhrases.append(phrase)
            self.allPhrases.append(phrase)
        
    def import_legacy_settings(self, configFilePath):
        """
        Import an abbreviations settings file from v0.4x.x.
        
        @param configFilePath: full path to the abbreviations file
        """
        importer = LegacyImporter()
        importer.load_config(configFilePath)        
        folder = PhraseFolder(DEFAULT_ABBR_FOLDER)
        
        # Check phrases for unique abbreviations
        for phrase in importer.phrases:
            if not self.check_abbreviation_unique(phrase.abbreviation, phrase):
                raise ImportException("The abbreviation '" + phrase.abbreviation + "' is already in use.")
        return (folder, importer.phrases)
    
    def check_abbreviation_unique(self, abbreviation, targetPhrase):
        """
        Checks that the given abbreviation is not already in use.
        
        @param abbreviation: the abbreviation to check
        @param targetPhrase: the phrase for which the abbreviation to be used 
        """
        for item in self.allFolders:
            if PhraseMode.ABBREVIATION in item.modes:
                if item.abbreviation == abbreviation:
                    return item is targetPhrase
            
        for item in self.allPhrases:
            if PhraseMode.ABBREVIATION in item.modes:
                if item.abbreviation == abbreviation:
                    return item is targetPhrase
        
        return True
            
    def check_hotkey_unique(self, modifiers, hotKey, targetPhrase):
        """
        Checks that the given hotkey is not already in use. Also checks the 
        special hotkeys configured from the advanced settings dialog.
        
        @param modifiers: modifiers for the hotkey
        @param abbreviation: the hotkey to check
        @param targetPhrase: the phrase for which the abbreviation to be used         
        """
        for item in self.allFolders:
            if PhraseMode.HOTKEY in item.modes:
                if item.modifiers == modifiers and item.hotKey == hotKey:
                    return item is targetPhrase
            
        for item in self.allPhrases:
            if PhraseMode.HOTKEY in item.modes:
                if item.modifiers == modifiers and item.hotKey == hotKey:
                    return item is targetPhrase     

        for item in self.globalHotkeys:
            if item.enabled:
                if item.modifiers == modifiers and item.hotKey == hotKey:
                    return False

        return True
    
# Legacy Importer ----

# Legacy configuration sections
CONFIG_SECTION = "config"
DEFAULTS_SECTION = "defaults"
ABBR_SECTION = "abbr"

# Legacy configuration parameters

WORD_CHARS_REGEX_OPTION = "wordchars"
IMMEDIATE_OPTION = "immediate"
IGNORE_CASE_OPTION = "ignorecase"
MATCH_CASE_OPTION = "matchcase"
BACKSPACE_OPTION = "backspace"
OMIT_TRIGGER_OPTION = "omittrigger"
TRIGGER_INSIDE_OPTION = "triggerinside"

ABBREVIATION_OPTIONS = [
                        WORD_CHARS_REGEX_OPTION,
                        IMMEDIATE_OPTION,
                        IGNORE_CASE_OPTION,
                        MATCH_CASE_OPTION,
                        BACKSPACE_OPTION,
                        OMIT_TRIGGER_OPTION,
                        TRIGGER_INSIDE_OPTION
                        ]

class LegacyImporter:
    
    def load_config(self, configFilePath):
        try:
            config = configobj.ConfigObj(configFilePath, list_values=False)
        except Exception, e:
            raise ImportException(str(e))
        abbrDefinitions = config[ABBR_SECTION]
        
        definitions = abbrDefinitions.keys()
        definitions.sort()        

        # Import default settings
        #defaultSettings = dict(p.items(DEFAULTS_SECTION))
        defaultSettings = config[DEFAULTS_SECTION]
        defaultSettings[WORD_CHARS_REGEX_OPTION] = re.compile(defaultSettings[WORD_CHARS_REGEX_OPTION], re.UNICODE)
        
        self.__applyBooleanOption(IMMEDIATE_OPTION, defaultSettings)        
        self.__applyBooleanOption(IGNORE_CASE_OPTION, defaultSettings)
        self.__applyBooleanOption(MATCH_CASE_OPTION, defaultSettings)   
        self.__applyBooleanOption(BACKSPACE_OPTION, defaultSettings)    
        self.__applyBooleanOption(OMIT_TRIGGER_OPTION, defaultSettings)
        self.__applyBooleanOption(TRIGGER_INSIDE_OPTION, defaultSettings)        
        
        # Import user-defined abbreviations as phrases        
        self.phrases = []
        
        while len(definitions) > 0:

            # Flush any unused options that weren't matched with an abbreviation definition
            while '.' in definitions[0]:
                isOption = False
                for option in ABBREVIATION_OPTIONS:
                    if definitions[0].endswith(option):
                        definitions.pop(0)
                        isOption = True
                        break

                if len(definitions) == 0:
                    break # leave the flushing loop if no definitions remaining
                if len(definitions) == 1 and not isOption:
                    break # leave the flushing loop if the last remaining definition is not an option
                    

            if len(definitions) > 0:
                self.phrases.append(self.__buildPhrase(definitions, abbrDefinitions, defaultSettings))                 

    def __buildPhrase(self, definitions, abbrDefinitions, defaults):
        """
        Create a new Phrase instance for the abbreviation definition at the start of the list
        
        @param definitions: list of definitions yet to be processed, with the abbreviation definition
        to be instantiated at the start of the list
        @param abbrDefinitions: dictionary of all abbreviation and config definitions
        """
        ownSettings = {}
        definition = definitions.pop(0)
        phraseText = abbrDefinitions[definition]
        startString = definition + '.'
        offset = len(startString)

        while len(definitions) > 0:
            key = definitions[0]
            if key.startswith(startString):
                ownSettings[key[offset:]] = abbrDefinitions[key]
                definitions.pop(0)
            else:
                # no more options for me - leave loop
                break
        
        if ownSettings.has_key(WORD_CHARS_REGEX_OPTION):
            ownSettings[WORD_CHARS_REGEX_OPTION] = re.compile(ownSettings[WORD_CHARS_REGEX_OPTION], re.UNICODE)
        
        self.__applyBooleanOption(IMMEDIATE_OPTION, ownSettings)        
        self.__applyBooleanOption(IGNORE_CASE_OPTION, ownSettings)
        self.__applyBooleanOption(MATCH_CASE_OPTION, ownSettings)   
        self.__applyBooleanOption(BACKSPACE_OPTION, ownSettings)    
        self.__applyBooleanOption(OMIT_TRIGGER_OPTION, ownSettings)
        self.__applyBooleanOption(TRIGGER_INSIDE_OPTION, ownSettings)
        
        #if result._getSetting(IGNORE_CASE_OPTION):
        #    result.abbreviation = result.abbreviation.lower()
        
        # Apply options to final phrase
        phraseDescription = phraseText[:20].replace('\n', ' ')
        result = Phrase(phraseDescription, phraseText)
        result.set_abbreviation(definition)
        result.set_modes([PhraseMode.ABBREVIATION])
        result.wordChars = self.__getDefaultOrCustom(defaults, ownSettings, WORD_CHARS_REGEX_OPTION)
        result.immediate = self.__getDefaultOrCustom(defaults, ownSettings, IMMEDIATE_OPTION)
        result.ignoreCase = self.__getDefaultOrCustom(defaults, ownSettings, IGNORE_CASE_OPTION)
        result.matchCase = self.__getDefaultOrCustom(defaults, ownSettings, MATCH_CASE_OPTION)
        result.backspace = self.__getDefaultOrCustom(defaults, ownSettings, BACKSPACE_OPTION)
        result.omitTrigger = self.__getDefaultOrCustom(defaults, ownSettings, OMIT_TRIGGER_OPTION)
        result.triggerInside = self.__getDefaultOrCustom(defaults, ownSettings, TRIGGER_INSIDE_OPTION)
        return result
            
    def __applyBooleanOption(self, optionName, settings):
        if settings.has_key(optionName):
            settings[optionName] = (settings[optionName].lower()[0] == 't')
            
    def __getDefaultOrCustom(self, defaults, ownSettings, optionName):
        if ownSettings.has_key(optionName):
            return ownSettings[optionName]
        else:
            return defaults[optionName]

# This import placed here to prevent circular import conflicts
from phrase import *

class GlobalHotkey(AbstractHotkey):
    """
    A global application hotkey, configured from the advanced settings dialog.
    Allows a method call to be attached to the hotkey.
    """
    
    def __init__(self):
        AbstractHotkey.__init__(self)
        self.enabled = False
        self.windowTitleRegex = None
    
    def set_closure(self, closure):
        """
        Set the callable to be executed when the hotkey is triggered.
        """
        self.closure = closure
        
    def check_hotkey(self, modifiers, key, windowTitle):
        if AbstractHotkey.check_hotkey(self, modifiers, key, windowTitle) and self.enabled:
            _logger.debug("Triggered global hotkey using modifiers: %s key: %s" % (repr(modifiers), key))
            self.closure()
        return False

