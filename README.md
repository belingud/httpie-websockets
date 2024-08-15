# httpie-websockets

[![PyPI version](https://img.shields.io/pypi/v/httpie-websockets?style=for-the-badge)](https://pypi.org/project/httpie-websockets/) [![License](https://img.shields.io/github/license/belingud/httpie-websockets.svg?style=for-the-badge)](https://opensource.org/licenses/MIT) ![Static Badge](https://img.shields.io/badge/language-Python-%233572A5?style=for-the-badge) ![PyPI - Downloads](https://img.shields.io/pypi/dm/httpie-websockets?logo=python&style=for-the-badge) ![Pepy Total Downlods](https://img.shields.io/pepy/dt/httpie-websockets?style=for-the-badge&logo=python)

Home: https://github.com/belingud/httpie-websockets


<!-- TOC -->
* [httpie-websockets](#httpie-websockets)
  * [Features](#features)
  * [Install](#install)
  * [Usage](#usage)
    * [Debug Log](#debug-log)
    * [Proxy & Cert](#proxy--cert)
    * [Headers](#headers)
    * [Subprotocol](#subprotocol)
    * [Auth](#auth)
    * [Session](#session)
    * [Verify](#verify)
    * [Timeout](#timeout)
  * [Multi-line Input Support](#multi-line-input-support)
  * [Uninstall](#uninstall)
<!-- TOC -->

`httpie-websockets` is an HTTPie CLI plugin that adds WebSocket support to the HTTPie command line.

## Features

- **WebSocket Support:** Seamlessly connect to WebSocket servers using the familiar HTTPie command line interface.
- **Bidirectional Communication:** Send and receive messages in real-time.
- **Secure Connections:** Supports both `ws://` and `wss://` protocols.
- **Easy Integration:** Simple installation and usage within the HTTPie environment.

## Install

You can install by httpie plugins command:

```shell
httpie plugins install httpie-websockets
```

or use pip in the same environment with httpie

```shell
pip install httpie-websockets
```

If your `httpie` is installed with `pipx`, you also can use `pipx` to install `httpie-websockets`, If you cannot use it
properly after installation。

Suppose your httpie environment is named httpie.

```shell
# Replace httpie with your httpie venv name
pipx inject httpie httpie-websockets  # will auto upgrade version
# or
pipx runpip httpie install -U httpie-websockets
```

## Usage

After install this plugin, just pass websocket url to `http` command.

```shell
http ws://localhost:8000/ws
```

This allows HTTPie to interact with WebSocket servers directly from the command line.

Example:

```shell
$ http wss://echo.websocket.org
> wss://echo.websocket.org
Type a message and press enter to send it
Type 'exit' to close the connection

```

When you press CTRL+C, connection will disconnect and httpie will get handshake response headers
and websocket connection info with close code and close message like below:

```shell
^C
Oops! Disconnecting. Need to force quit? Press again!
HTTP/1.1 200 
connection: Upgrade
date: Thu, 15 Aug 2024 13:24:10 GMT
fly-request-id: 01J5B3BHGV549MMJQ474SF7J60-sin
sec-websocket-accept: MV41qn7qZQP3IXsTzYS5eDRe2tE=
server: Fly/ddfe15ec (2024-08-14)
upgrade: websocket
via: 1.1 fly.io

Websocket connection info:
Close Code: 1006
Close Msg: KeyboardInterrupt
```

### Debug Log

You can set `HTTPIE_WS_LOG_LEVEL` to `DEBUG` to see `httpie_websocket` debug log for more information.

On linux and Mac:

```shell
export HTTPIE_WS_LOG_LEVEL=DEBUG
```
Or

```shell
HTTPIE_WS_LOG_LEVEL=DEBUG http wss://echo.websocket.org
```

On Windows:

```shell
set HTTPIE_WS_LOG_LEVEL=DEBUG
```

Or

```shell
# Powershell
$env:HTTPIE_WS_LOG_LEVEL="DEBUG"; http wss://echo.websocket.org
# Cmd
cmd /C "set HTTPIE_WS_LOG_LEVEL=DEBUG &&; http wss://echo.websocket.org"
```

### Proxy & Cert

This project using `websocket-client` to establish connection, support proxy and custom cert file.
You can pass proxy and cert to httpie.

Support `http`, `socks4`, `socks4a`, `socks5` and `socks5h` proxy protocol.

```shell
http wss://echo.websocket.org --proxy=http://proxy.com
http wss://echo.websocket.org --proxy=socks4://proxy.com
http wss://echo.websocket.org --proxy=socks4a://proxy.com
http wss://echo.websocket.org --proxy=socks5://proxy.com
http wss://echo.websocket.org --proxy=socks5h://proxy.com
```

Custom cert file same as httpie.

```shell
http wss://yourservice.com --cert=/path/to/cert --cert-key=/path/to/cert-key --cert-key-pass=pass
```

### Headers

Also support custom headers, you can send header through httpie.

**Note** `wss://echo.websocket.org` does not support any authentication, and will ignore any headers you send.


```shell
http wss://echo.websocket.org Custom-Header:Custom-value
```

### Subprotocol

You can send subprotocols from the headers.
Multiple subprotocols need to be separated by commas, since httpie receives only the first one with the same headers key.

```shell
http wss://echo.websocket.org Sec-WebSocket-Protocol:sub1,sub2
```

### Auth

Support pass auth option and auth-type.

**basic**: httpie use basic auth as default.

```shell
http wss://echo.websocket.org --auth=user1:pass
```

Websocket server will receive a header like `'Authorization': 'Basic dXNlcjE6dGVzdA=='`.

**bearer**: similar with basic.

```shell
http wss://echo.websocket.org --auth-type=bearer --auth=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

Websocket server will receive a header like `'Authorization': 'Bearer eyxxxx'`

**digest**: Technically, digest authentication is not supported, but you can generate an auth
header manually if you want.

```shell
http wss://echo.websocket.org "Authorization: Digest username='user', realm='example', nonce='c3a7f38c-5e5a-45b2-a5b5-3b5e2c5c5c5c', uri='/path/to/protected/resource', response='generated_response', qop=auth, nc=00000001, cnonce='generated_cnonce', opaque='6d6b8f8f-6b8f-6b8f-6b8f-6b8f6b8f6b8f'"
```

### Session

Support session option and perform as a header.

```shell
http wss://echo.websocket.org -s user1
```

Similar like basic auth, server will receive a header like `'Authorization': 'Basic dXNlcjE6dGVzdA=='`.

### Verify

You can disable SSL verification by using the --verify=no option

```shell
http wss://echo.websocket.org --verify=no
```

### Timeout

Pass time out option to waiting for connection establish.

```shell
http wss://echo.websocket.org --timeout=3
```

## Multi-line Input Support

Coming soon.

## Uninstall

If you want to uninstall this plugin, use the same way when you install.

Installed by `httpie` command, uninstall by

```shell
httpie plugins uninstall httpie-websockets
```

Installed by `pip` command, uninstall by

```shell
pip uninstall httpie-websockets
```
