
---
## [1.0.0](https://github.com/belingud/httpie-websockets/compare/v0.6.1..v1.0.0) - 2024-10-05

### 🚜 Refactor

- **(websockets)** Remove unused attribute "_msgs_bytes" from WebsocketAdapter - ([964dcda](https://github.com/belingud/httpie-websockets/commit/964dcda4d1489d23f476868bdd4430cdc426d201)) - belingud
- Rename method in WebsocketAdapter class for clarity - ([388d937](https://github.com/belingud/httpie-websockets/commit/388d937eb41d7fa8540ff1efaaab6590f8f81064)) - belingud
- Updated proxy URL to Hong Kong in get_proxy function - ([4057107](https://github.com/belingud/httpie-websockets/commit/405710763e5fdaf2ad7e1fadb4462bc16673dd88)) - belingud

### 📚 Documentation

- Update CHANGELOG for v0.6.1 release - ([0638795](https://github.com/belingud/httpie-websockets/commit/0638795498efd0a33a644c0dea52cd14988c7be3)) - belingud

# Changelog
All notable changes to this project will be documented in this file. See [conventional commits](https://www.conventionalcommits.org/) for commit guidelines.


---
## [0.6.1](https://github.com/belingud/httpie-websockets/compare/v0.6.0..v0.6.1) - 2024-09-14

### 🐛 Bug Fixes

- Correct newline handling in stdin read - ([20d8285](https://github.com/belingud/httpie-websockets/commit/20d82859415a81829ec67303be9560da8c622ac2)) - belingud

### 🧪 Testing

- Refactor proxy test setup and add end-with-whitespace tests - ([d580559](https://github.com/belingud/httpie-websockets/commit/d5805590dd584f4e34501e235813bc34e29e431c)) - belingud

### ⚙️ Miscellaneous Tasks

- Update pyproject.toml and pyrightconfig.json - ([d7d2077](https://github.com/belingud/httpie-websockets/commit/d7d207761e29189e325a30a33c131e8b09b52e17)) - belingud
- Update CHANGELOG and scripts for new features and fixes - ([1e5048e](https://github.com/belingud/httpie-websockets/commit/1e5048ee16e5b0275e3fac9c26c7f2c1385dee98)) - belingud


---
## [0.6.0](https://github.com/belingud/httpie-websockets/compare/v0.5.4..v0.6.0) - 2024-09-13

### ⛰️  Features

- Add multiple line input support, escape odd backslashes at the end-of-line - ([5ea72d8](https://github.com/belingud/httpie-websockets/commit/5ea72d8d82fa2a36f0bbc257f7c078303a224157)) - belingud
- Add changelog generation script - ([d1f5e37](https://github.com/belingud/httpie-websockets/commit/d1f5e37ae8bda34657b6c5d91258fe5e72835cbc)) - belingud
- Update changelog formatting and parser configuration - ([df3bcf4](https://github.com/belingud/httpie-websockets/commit/df3bcf4415d649a989bef4aa116833205c84fa80)) - belingud
- Remove deprecated Makefile and Messages Download functionality - ([c7f5050](https://github.com/belingud/httpie-websockets/commit/c7f505085b160652cf9dd01427ca5209b47c113d)) - belingud

### 📚 Documentation

- Update README and CHANGELOG for new features and fixes - ([7cc5b91](https://github.com/belingud/httpie-websockets/commit/7cc5b9174f9dcd912e135773af12d41abf7eb1e5)) - belingud


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
