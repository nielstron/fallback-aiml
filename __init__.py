# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


import aiml
import os
from os import listdir, remove as remove_file
from os.path import dirname, isfile

from mycroft.api import DeviceApi
from mycroft.skills.core import FallbackSkill, intent_handler, intent_file_handler
from adapt.intent import IntentBuilder
from mycroft.util.log import getLogger

__author__ = 'jarbas, nielstron'

LOGGER = getLogger(__name__)

class AimlFallback(FallbackSkill):

    def __init__(self):
        super(AimlFallback, self).__init__(name='AimlFallback')
        self.kernel = aiml.Kernel()
        self.aiml_path = os.path.join(dirname(__file__),"aiml")
        self.brain_path = os.path.join(dirname(__file__), "brain", "bot_brain.brn")
        self.load_brain()
        self.converse_mode = False
        return

    def initialize(self):
        self.register_fallback(self.handle_fallback, 90)
        return

    def load_brain(self):
        if isfile(self.brain_path):
            self.kernel.bootstrap(brainFile = self.brain_path)
        else:
            aimls = listdir(self.aiml_path)
            for aiml in aimls:
                self.kernel.learn(os.path.join(self.aiml_path, aiml))
            self.kernel.saveBrain(self.brain_path)
        device = DeviceApi().get()
        self.kernel.setBotPredicate("name", device["name"])
        self.kernel.setBotPredicate("species", device["type"])
        self.kernel.setBotPredicate("genus", "Mycroft")
        self.kernel.setBotPredicate("family", "virtual personal assistant")
        self.kernel.setBotPredicate("order", "artificial intelligence")
        self.kernel.setBotPredicate("class", "computer program")
        self.kernel.setBotPredicate("kingdom", "machine")
        self.kernel.setBotPredicate("hometown", "127.0.0.1")
        self.kernel.setBotPredicate("botmaster", "master")
        self.kernel.setBotPredicate("master", "the community")
        # IDEA: extract age from https://api.github.com/repos/MycroftAI/mycroft-core created_at date
        self.kernel.setBotPredicate("age", "2")
        return

    @intent_handler(IntentBuilder("ResetMemoryIntent").require("Reset").require("Memory"))
    def handle_reset_brain(self, message):
        # delete the brain file and reset memory
        self.speak_dialog("reset.memory")
        self.kernel.resetBrain()
        remove_file(self.brain_path)
        # also reload base knowledge
        self.load_brain()
        return

    def ask_brain(self, utterance):
        response = self.kernel.respond(utterance)
        # make a security copy once in a while
        # TODO maybe every 10th time?
        self.kernel.saveBrain(self.brain_path)
        return response

    def converse(self, utterances, lang="en-us"):
        # TODO handle end conversation intents to end conversation
        if not self.converse_mode or self._check_end(utterances[0]):
            self.converse_mode = False
            return False

        self.converse_mode = self._answer(utterances[0])
        return self.converse_mode

    @intent_file_handler('chat.intent')
    def start_conversation(self, message):
        self.converse_mode = True
        return self.handle_fallback(message)
    
    @intent_file_handler('chat.end.intent')
    def end_conversation(self, message):
        self.converse_mode = False
        return self.handle_fallback(message)
    
    def _check_end(self, query):
        """
        Workaround to check if conversation should be stopped
        
        Return:
            True if query contains conversation ending hotwords
        """
        for keyword in ("end", "stop"):
            if keyword in query:
                return True
        return False
    
    def handle_fallback(self, message):
        query = message.data.get("utterance")
        return self._answer(query)

    def _answer(self, query):
        """Return answer to string query (directly outputted)"""
        answer = self.ask_brain(query)
        if self.converse_mode and answer == "":
            query = "random pick up line"
            answer = self.ask_brain(query)
        if answer != "":
            asked_question = False
            if answer.endswith("?"):
                asked_question = True
            self.speak(answer, expect_response=asked_question)
            return True
        return False

    def shutdown(self):
        self.kernel.resetBrain()
        self.remove_fallback(self.handle_fallback)
        super(AimlFallback, self).shutdown()

    def stop(self):
        self.converse_mode = False
        pass

def create_skill():
    return AimlFallback()
