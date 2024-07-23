# httpie-websockets

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

Installed by `httpie` command, uninstall by `httpie plugins uninstall httpie-websockets`
Installed by `pip` command, uninstall by `pip uninstall httpie-websockets`

