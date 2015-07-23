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
import sys
from pyvirtualdisplay import Display
from selenium import webdriver
import uuid
from multipart import encode_multipart_formdata
from PIL import Image
from cStringIO import StringIO


class FluentBot(object):

    def __init__(self):
        AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
        self.context = ('', '')
        self.offset = None
        self.client = AsyncHTTPClient()
        self.token = open("token.txt", "r").read().strip()
        self.base_url = "https://api.telegram.org/bot" + self.token
        try:
            self.patterns = pickle.load(open("patterns.obj", "r"))
        except Exception:
            self.patterns = []
        self.display = Display(visible=0, size=(150, 100))
        self.display.start()
        self.ingress_pattern = "https://www.ingress.com/intel?ll=%(latitude)s,%(longitude)s&z=14"


    def start(self):
        self._getUpdates(self._handle_update)
        ioloop.IOLoop.instance().start()

    def stop(self):
        self.display.stop()
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
            self.handle_location(message)
            return
        text = message[u'message'][u'text']
        chat = message[u'message'][u'chat'][u'id']
        username = message[u'message'][u'from'][u'first_name']
        command_prefix = [
                u'/',
                u'@FluentBot, ',
                u'@FluentBot ',
                u'@Fluentbot, ',
                u'@Fluentbot ',
                u'@Fluffy, ',
                u'@Fluffy ']
        is_command = False
        for i in command_prefix:
            if text.startswith(i):
                self._dispatch_command(chat, username, text[len(i):])
                is_command = True
        if not is_command:
            self._dispatch_text(chat, username, text)

    def handle_location(self, message):
        if message[u'message'].has_key(u'location'):
            fp = webdriver.FirefoxProfile(sys.argv[1])
            browser = webdriver.Firefox(firefox_profile=fp)
            browser.get(self.ingress_pattern % message[u'message'][u'location'])
            ioloop.IOLoop.instance().add_timeout(time.time() + 10,
                lambda: self._sendScreenshot(browser, message))

    def _sendScreenshot(self, browser, message):
        imgdata = browser.get_screenshot_as_png()
        browser.quit()
        im = Image.open(StringIO(imgdata))
        im = im.crop((0, 130, im.size[0], im.size[1] - 130))
        photo = StringIO()
        im.save(photo, 'PNG')
        data = photo.getvalue()
        photo.close()
        self._sendPhoto(message[u'message'][u'chat'][u'id'], data)

    def _dispatch_text(self, chat, username, text):
        matched = []
        for i in self.patterns:
            if i[0].match(text):
                matched.append(i)
        if matched:
            reply = random.choice(matched)
            self.context = reply
            self._sendMessage(chat, random.choice(matched)[1].replace("%u", username))

    def _dispatch_command(self, chat, username, text):
        command = text.split(u' ')[0]
        if command in (u'если', u'if'):
            self._dispatch_command_cond(username, chat, text)
        if command in (u'забудь', u'forget'):
            try:
                self.patterns.remove(self.context)
            except ValueError:
                pass
        if command in (u'запомни', u'save'):
            pickle.dump(self.patterns, open('patterns.obj', 'w'))

    def _dispatch_command_cond(self, commander, chat, text):
        try:
            pattern = text.split(u"'")[1]
            reproduce = text.split(u"'")[3]
            self.patterns.append((re.compile(pattern, flags=re.I + re.U), reproduce))
        except Exception:
            self._sendMessage(chat, u"%s, train me better!" % commander)

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

    def _sendPhoto(self, chat_id, photo, **args):
        content_type, body = encode_multipart_formdata([('chat_id', str(chat_id))], [('photo', 'screen.png', photo)])
        self.client.fetch(self.base_url + "/sendPhoto",
            method = 'POST',
            headers = {'content-length': str(len(body)), 'content-type': content_type},
            body = body,
            callback = lambda x: x)

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
