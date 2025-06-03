import hashlib
import ssl
import io
import os
import urllib.parse
from typing import List

import certifi
from PIL import Image

from flask import Flask, make_response, abort, redirect, request
from flask_ldapconn import LDAPConn
from flask_apscheduler import APScheduler


def strtobool(str_in: str) -> bool:
    if str_in.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif str_in.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise Exception('Invalid boolean value')


class Config:
    LDAP_SERVER = os.environ.get('LDAP_SERVER')
    LDAP_PORT = int(os.environ.get('LDAP_PORT', default=389))
    LDAP_BINDDN = os.environ.get('LDAP_BINDDN', default=None)
    LDAP_SECRET = os.environ.get('LDAP_BINDPW', default=None)
    LDAP_USE_SSL = strtobool(os.environ.get('LDAP_SSL', default='False'))
    LDAP_USE_TLS = strtobool(os.environ.get('LDAP_TLS', default='True'))
    LDAP_SEARCH_BASE = os.environ.get('LDAP_SEARCH_BASE')
    LDAP_CONNECT_TIMEOUT = 10  # Honored when the TCP connection is being established
    LDAP_READ_ONLY = True
    LDAP_TLS_VERSION = ssl.PROTOCOL_TLSv1_2
    LDAP_CA_CERTS_FILE = certifi.where()
    FORCE_ATTRIBUTE_VALUE_AS_LIST = True
    CALCULATE_HASHES_DELAY = int(os.environ.get('CALCULATE_HASHES_DELAY', default=600))
    SCHEDULER_API_ENABLED = True
    MAX_SIZE = 2048


ldap = LDAPConn()


class User(ldap.Entry):
    base_dn = Config.LDAP_SEARCH_BASE
    object_classes = ['inetOrgPerson']

    emails: List[str] = ldap.Attribute('mail')
    photo: List[bytes] = ldap.Attribute('jpegPhoto')


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # TODO: use sqlite/redis/memcached
    mail_hashes_md5 = dict()
    mail_hashes_sha256 = dict()

    scheduler = APScheduler()

    ldap.init_app(app)
    scheduler.init_app(app)

    @app.get("/avatar/<mail_hash>")
    def get_photo(mail_hash):
        mail = None

        if mail_hash in mail_hashes_md5:
            mail = mail_hashes_md5.get(mail_hash)
        elif mail_hash in mail_hashes_sha256:
            mail = mail_hashes_sha256.get(mail_hash)

        s = None
        if 's' in request.args:
            s = request.args.get('s', type=int, default=80)
        if 'size' in request.args:
            s = request.args.get('size', type=int, default=80)

        if not s:
            size = 80
        elif s < 1:
            size = 80
        elif s > Config.MAX_SIZE:
            size = Config.MAX_SIZE
        else:
            size = s

        # default action
        d = None  # default
        if 'd' in request.args:
            d = request.args.get('d', type=str)
        if 'default' in request.args:
            d = request.args.get('default', type=str)

        # force
        f = None  # default
        if 'f' in request.args:
            f = request.args.get('f', type=str)

        if mail and not f:
            user: User = User.query.filter("mail:{}".format(mail)).first()
            if user and len(user.photo) > 0:
                photo = user.photo[0]
                if photo and len(photo) > 0:
                    pil_photo: Image.Image = Image.open(io.BytesIO(photo))
                    pil_photo = make_square(pil_photo)
                    pil_photo = pil_photo.resize((size, size))
                    photo_new = io.BytesIO()
                    pil_photo.save(photo_new, format='PNG')
                    # TODO: store photo in cache
                    response = make_response(photo_new.getvalue())
                    response.headers.set('Content-Type', 'image/png')
                    response.headers.set('Cache-Control', 'max-age=3600')
                    return response

        # if no image was found, but a default action is given
        if d == '404':
            return abort(404)

        param_dict = dict()
        if d:
            param_dict['d'] = d
        if f:
            param_dict['f'] = f
        if s:
            param_dict['s'] = s

        url = "https://cdn.libravatar.org/avatar/{}".format(mail_hash)

        params = urllib.parse.urlencode(param_dict)
        if params:
            url += "?{}".format(params)

        return redirect(url, 302)

    @scheduler.task('interval', seconds=Config.CALCULATE_HASHES_DELAY)
    def calculate_hashes():
        print("calculating hashes of known mail addresses")

        with app.app_context():

            users = User.query.all()
            for index, user in enumerate(users):
                email_addresses = []

                for email in user.emails:
                    email.strip().lower()
                    if email not in email_addresses:
                        email_addresses.append(email)

                for email in email_addresses:
                    email_md5 = hashlib.md5(email.encode('ascii')).hexdigest()
                    email_sha256 = hashlib.sha256(email.encode('ascii')).hexdigest()

                    mail_hashes_md5[email_md5] = email
                    mail_hashes_sha256[email_sha256] = email

    calculate_hashes()
    scheduler.start()

    return app


# copied from https://stackoverflow.com/a/44231784 and adapted
def make_square(im: Image.Image, fill_color=(0, 0, 0, 0)) -> Image.Image:
    x, y = im.size
    size = min(x, y)
    new_im = Image.new('RGBA', (size, size), fill_color)
    new_im.paste(im, (int((size - x) / 2), int((size - y) / 2)))
    return new_im
