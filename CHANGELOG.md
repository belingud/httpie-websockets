## New in 0.5.0

1. Support proxy passed by httpie, like `http wss://echo.websocket.org --proxy=http://proxy.server`
2. Support custom ssl cert file with httpie, like `http wss://echo.websocket.org --cery=/path/to/cert`
3. Set env `HTTPIE_WS_LOG_LEVEL` to `DEBUG` to see more debug info from httpie_websockets

## New in 0.4.0

1. Can not type exit or quit to close
2. Fix hangup when closed by server

## New in 0.3.1

1. fix hangup when cannot connect server

## New in 0.3.0

1. Windows command line support

## New in 0.2.1

1. Add more handling of connection establishment exceptions
2. Support both `exit` and `quit` message to quit the command

## New in 0.2.0

1. Add websocket response headers output, default close reason is empty
2. Fix server close connection will cause block and no action in command-line
