# Changelog
All notable changes to this project will be documented in this file. See [conventional commits](https://www.conventionalcommits.org/) for commit guidelines.

---
## [0.5.4](https://github.com/belingud/httpie-websockets/compare/v0.5.3..v0.5.4) - 2024-08-22

### ⛰️  Features

- Update WebsocketAdapter to handle WebSocket connections correctly - ([811dd23](https://github.com/belingud/httpie-websockets/commit/811dd2343ac8c4120dc306c7a82ca293b60bb3a0)) - belingud

### 🐛 Bug Fixes

- fix version string - ([932cc92](https://github.com/belingud/httpie-websockets/commit/932cc924831498b3298436cc8a0e55e0eefb14c5)) - belingud
- Should not wait for response - ([5c3e4b0](https://github.com/belingud/httpie-websockets/commit/5c3e4b0988efecb58fb3062584aadd3b61557048)) - belingud

---

> Please ignore version 0.5.1/0.5.2/0.5.3, functionally defects.

## 0.5.0

1. Support proxy passed by httpie, like `http wss://echo.websocket.org --proxy=http://proxy.server`
2. Support custom ssl cert file with httpie, like `http wss://echo.websocket.org --cery=/path/to/cert`
3. Set env `HTTPIE_WS_LOG_LEVEL` to `DEBUG` to see more debug info from httpie_websockets

## 0.4.0

1. Can not type exit or quit to close
2. Fix hangup when closed by server

## 0.3.1

1. fix hangup when cannot connect server

## 0.3.0

1. Windows command line support

## 0.2.1

1. Add more handling of connection establishment exceptions
2. Support both `exit` and `quit` message to quit the command

## 0.2.0

1. Add websocket response headers output, default close reason is empty
2. Fix server close connection will cause block and no action in command-line
