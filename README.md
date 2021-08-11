# libravatar-ldap-jpegphoto
Libravatar compatible API which relies on the jpegphoto LDAP attribute

## How it works

This project implements the avatar endpoint known from Gravatar and Libravatar (See https://wiki.libravatar.org/api/).

Because the Gravatar/Libravatar API uses hashes (md5/sha256) and not plaintext email addresses, we have to keep a map of hashes for all known mail addresses.
Therefore, on each startup and also every X seconds, this app calculates both hashes (md5/sha256) for each user's mail address and stores them in memory.

If a picture is being requested, this app looks up the mail address first, by using the given hash and the prebuilt in-memory dictionaries.
Then, the LDAP lookup for the user and their `jpegphoto` attribute will be done using the cleartext email address.

If the user was found and if they have a picture, the picture will be cropped, resized and converted to the PNG format.

## Usage

There are the following environment arguments:

- `LDAP_SERVER` LDAP server (required)
- `LDAP_BINDDN` LDAP bind dn (default: None)
- `LDAP_BINDPW` LDAP bind password (default: None)
- `LDAP_PORT` LDAP port (default: 389)
- `LDAP_TLS` whether to use STARTTLS (default: True)
- `LDAP_SSL` whether to enable TLS/SSL (default: False)
- `LDAP_SEARCH_BASE` LDAP tree where to search for user accounts (required)
- `CALCULATE_HASHES_DELAY` interval in seconds, how often to calculate hashes **for all users** (default: 600)

### Docker

```
docker run \
    -e LDAP_SERVER=ipa.example.org \
    -e LDAP_BINDDN=uid=libravatar-ldap,cn=sysaccounts,cn=etc,dc=example,dc=org \
    -e LDAP_BINDPW=Secret1234 \
    -e LDAP_PORT=636 \
    -e LDAP_TLS=False \
    -e LDAP_SSL=True \
    -e LDAP_SEARCH_BASE=cn=users,cn=accounts,dc=example,dc=org \
    -p 8080:5000 \
    jasperroloff/libravatar-ldap-jpegphoto
```

### Docker-Compose

Use the `docker-compose.yml` from this repo.

### Kubernetes

Helm Chart is Work in Progress

## Licence

See [LICENSE](LICENSE)
