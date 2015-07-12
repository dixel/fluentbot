#-*- coding: utf-8 -*-

from tornado.web import asynchronous
from tornado.httpclient import AsyncHTTPClient
from tornado import ioloop
import urllib
import json
import time
import random
import re
import pickle


class FluentBot(object):

    def __init__(self):
        AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
        self.offset = None
        self.client = AsyncHTTPClient()
        self.token = open("token.txt", "r").read().strip()
        self.base_url = "https://api.telegram.org/bot" + self.token
        try:
            self.patterns = pickle.load(open("patterns.obj", "r"))
        except Exception:
            self.patterns = {}

    def start(self):
        self._getUpdates(self._handle_update)
        ioloop.IOLoop.instance().start()

    def stop(self):
        ioloop.IOLoop.instance().stop()

    def _handle_update(self, response):
        if response[u'ok']:
            for i in response[u'result']:
                self._dispatch_message(i)
        ioloop.IOLoop.instance().add_timeout(time.time() + 2,
                lambda: self._getUpdates(self._handle_update))

    def _dispatch_message(self, message):
        if self.offset >= message[u'update_id']:
            return
        self.offset = message[u'update_id']
        if not message[u'message'].has_key(u'text'):
            return
        text = message[u'message'][u'text']
        chat = message[u'message'][u'chat'][u'id']
        username = message[u'message'][u'from'][u'first_name']
        if text[0] == u'/':
            self._dispatch_command(chat, username, text[1:])
        else:
            self._dispatch_text(chat, username, text)

    def _dispatch_text(self, chat, username, text):
        patterns = []
        if self.patterns.has_key(chat):
            if self.patterns[chat].has_key(username):
                patterns += self.patterns[chat][username]
            if self.patterns[chat].has_key(u'*'):
                patterns += self.patterns[chat][u'*']
        matched = []
        for i in patterns:
            if i[0].match(text):
                matched.append(i[1])
        if matched:
            self._sendMessage(chat, random.choice(matched).replace("%username", username))

    def _dispatch_command(self, chat, username, text):
        command = text.split(u' ')[0]
        if command == u'если' or command == 'if':
            self._dispatch_command_cond(chat, username, text.split(u' ')[1:])
        if command == u'запомни' or command == 'save':
            pickle.dump(self.patterns, open('patterns.obj', 'w'))

    def _dispatch_command_cond(self, chat, commander, text):
        if text[0] == u'кто-то':
            username = u'*'
        elif text[0] == u'%username':
            username = u'*'
        elif text[0] == u'кто-нибудь':
            username = u'*'
        elif text[0] == u'я':
            username = commander
        else:
            username = text[0]

        try:
            pattern = " ".join(text).split(u"'")[1]
            reproduce = " ".join(text).split(u"'")[3]
            if not self.patterns.has_key(chat):
                self.patterns[chat] = {}
            if not self.patterns[chat].has_key(username):
                self.patterns[chat][username] = []
            self.patterns[chat][username].append((re.compile(pattern), reproduce))
        except Exception:
            self._sendMessage(chat, u"%s, ты меня учить будешь пытаться? Делай это правильно!" % commander)

    def _basicResponseCallback(self, response, callback):
        result = {u'ok': False}
        if response.error:
            print "error: ", response.error
        else:
            try:
                result = json.loads(response.body)
            except Exception:
                pass
        callback(result)


    def _getMe(self, callback):
        self.client.fetch(self.base_url + "/getMe", callback)

    def _getUpdates(self, callback):
        kwargs = {
            'method': 'POST',
            'headers': {'content-type': 'application/x-www-form-urlencoded'},
            'callback': lambda response: self._basicResponseCallback(response, callback),
            'body': ''
        }
        if self.offset:
            kwargs['body'] = urllib.urlencode({
                "offset": self.offset
            })
        self.client.fetch(self.base_url + "/getUpdates", **kwargs)

    def _sendMessage(self, chat_id, message, **args):
        self.client.fetch(self.base_url + "/sendMessage",
            method = 'POST',
            headers = {'content-type': 'application/x-www-form-urlencoded'},
            body = urllib.urlencode({
                "chat_id": chat_id,
                "text": message.encode('utf-8')}),
            callback = lambda x: x)


if __name__ == '__main__':
    Fb = FluentBot()
    Fb.start()
