# process_commands.py
# module for working with process command I/O.
###### IMPORT ######

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import copy
import json
import os
import queue
import signal
import threading
import traceback

###### INTERNAL MODULES ######

from console_controls.console import *
import process_command.execute as pce

###### STATE ######

guiIsOpen = False
processCommandServer = None
processCommandServerThread = None
openCommandQueue = queue.Queue()
commandLock = threading.Lock()

PROCESS_COMMAND_HOST = '127.0.0.1'
try:
    PROCESS_COMMAND_PORT = int(os.environ.get('SYMPHONY_PROCESS_COMMAND_PORT', '7279'))
except ValueError:
    PROCESS_COMMAND_PORT = 7279
ENDPOINT_COMMANDS = ['retrieve', 'instantiate', 'export', 'convert', 'update_metadata']

###### FUNCTIONS ######

def successResponse(pc, payload=None):
    '''
    fields:
        pc (dict) - process command payload
        payload (dict | None) - response payload
    outputs: dict

    Builds a successful process command response.
    '''
    return {
        "status": "success",
        "id": pc.get('id'),
        "message": "",
        "payload": payload or {}
    }


def errorResponse(pc, message, payload=None):
    '''
    fields:
        pc (dict) - process command payload
        message (str) - error message identifier
        payload (dict | None) - response payload
    outputs: dict

    Builds an error process command response.
    '''
    return {
        "status": "error",
        "id": pc.get('id') if isinstance(pc, dict) else None,
        "message": message,
        "payload": payload or {}
    }


def runEndpointCommand(pc):
    '''
    fields:
        pc (dict) - process command payload
    outputs: dict

    Runs a command using the existing execution module and returns its response.
    '''
    command = pc['command']

    console.log(command + '...')

    if command == 'retrieve':
        return pce.retrieve(pc)
    elif command == 'instantiate':
        return pce.instantiate(pc)
    elif command == 'export':
        return pce.export(pc)
    elif command == 'convert':
        return pce.convert(pc)
    elif command == 'update_metadata':
        return pce.updateMetadata(pc)

    return errorResponse(pc, "UnknownCommandError")


def handleProcessCommandPayload(pc):
    '''
    fields:
        pc (dict) - process command payload
    outputs: tuple[dict | None, dict | None, bool]

    Executes a process command payload and returns the response, open command data,
    and whether the process should exit after the response is sent.
    '''
    global guiIsOpen

    if not isinstance(pc, dict) or pc.get('command') is None:
        return None, None, False

    if pc['command'] == 'kill':
        return successResponse(pc), None, True

    if pc['command'] == 'open':
        if guiIsOpen:
            return errorResponse(pc, "GuiAlreadyRunningError"), None, False

        guiIsOpen = True
        return successResponse(pc), copy.deepcopy(pc), False

    if pc['command'] in ENDPOINT_COMMANDS:
        try:
            return runEndpointCommand(pc), None, False
        except Exception:
            traceback.print_exc()
            return errorResponse(
                pc,
                "UnknownError",
                {"error_message": str(traceback.format_exc())}
            ), None, False

    return None, None, False


class ProcessCommandRequestHandler(BaseHTTPRequestHandler):
    '''
    HTTP handler for process command requests.
    '''

    server_version = 'SymphonyProcessCommandHTTP/1.0'

    def do_GET(self):
        '''
        fields: none
        outputs: nothing

        Provides a lightweight health check endpoint.
        '''
        if self.path != '/health':
            self.sendJson(404, {"status": "error", "message": "NotFound", "payload": {}})
            return

        self.sendJson(200, {"status": "success", "message": "", "payload": {"ready": True}})

    def do_POST(self):
        '''
        fields: none
        outputs: nothing

        Reads a JSON process command payload, executes it, and returns the response.
        '''
        if self.path not in ['/', '/process-command']:
            self.sendJson(404, {"status": "error", "message": "NotFound", "payload": {}})
            return

        try:
            contentLength = int(self.headers.get('Content-Length', '0'))
            rawBody = self.rfile.read(contentLength)
            pc = json.loads(rawBody.decode('utf-8'))
        except Exception:
            self.sendJson(400, errorResponse({}, "InvalidJsonError"))
            return

        with commandLock:
            response, openCommand, shouldExit = handleProcessCommandPayload(pc)

        if response is None:
            self.sendJson(400, errorResponse(pc, "InvalidCommandError"))
            return

        if openCommand is not None:
            openCommandQueue.put(openCommand)

        self.sendJson(200, response)

        if shouldExit:
            threading.Timer(0.1, lambda: os.kill(os.getpid(), signal.SIGTERM)).start()

    def log_message(self, format, *args):
        '''
        fields:
            format (str) - log format
            args (Any) - log format args
        outputs: nothing

        Routes HTTP logs through the existing console logger.
        '''
        console.log("process-command http: " + (format % args))

    def sendJson(self, statusCode, body):
        '''
        fields:
            statusCode (int) - HTTP status code
            body (dict) - JSON response body
        outputs: nothing

        Sends a JSON HTTP response.
        '''
        responseBytes = json.dumps(body).encode('utf-8')
        self.send_response(statusCode)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(responseBytes)))
        self.end_headers()
        self.wfile.write(responseBytes)


def startProcessCommandServer(host=PROCESS_COMMAND_HOST, port=PROCESS_COMMAND_PORT):
    '''
    fields:
        host (str) - interface to bind
        port (int) - port to listen on
    outputs: ThreadingHTTPServer

    Starts the localhost process command server on a background thread.
    '''
    global processCommandServer, processCommandServerThread

    if processCommandServer is not None:
        return processCommandServer

    processCommandServer = ThreadingHTTPServer((host, port), ProcessCommandRequestHandler)
    processCommandServerThread = threading.Thread(
        target=processCommandServer.serve_forever,
        name='SymphonyProcessCommandServer',
        daemon=True
    )
    processCommandServerThread.start()
    return processCommandServer


def stopProcessCommandServer():
    '''
    fields: none
    outputs: nothing

    Stops the process command server if it is running.
    '''
    global processCommandServer, processCommandServerThread

    if processCommandServer is None:
        return

    processCommandServer.shutdown()
    processCommandServer.server_close()
    processCommandServer = None
    processCommandServerThread = None


def waitForOpenCommand():
    '''
    fields: none
    outputs: dict

    Blocks until the HTTP server receives an open command.
    '''
    return openCommandQueue.get()


def setGuiIsOpen(isOpen):
    '''
    fields:
        isOpen (bool) - whether the editor UI is currently open
    outputs: nothing

    Updates process command state after the pygame window closes.
    '''
    global guiIsOpen

    guiIsOpen = isOpen

