# httpie-websockets

[![PyPI version](https://img.shields.io/pypi/v/httpie-websockets?style=for-the-badge)](https://pypi.org/project/httpie-websockets/) [![License](https://img.shields.io/github/license/belingud/httpie-websockets.svg?style=for-the-badge)](https://opensource.org/licenses/MIT) ![Static Badge](https://img.shields.io/badge/language-Python-%233572A5?style=for-the-badge) ![PyPI - Downloads](https://img.shields.io/pypi/dm/httpie-websockets?logo=pypi&style=for-the-badge)


Home: https://github.com/belingud/httpie-websockets

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

## Usage

After install this plugin, just pass websocket url to `http` command.

```shell
http ws://localhost:8000/ws
```

This allows HTTPie to interact with WebSocket servers directly from the command line.

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

